import os
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pyopencl as cl
from numba_pokemon_prngs.data import GENDER_SYMBOLS, NATURES_EN
from numba_pokemon_prngs.data.encounter import ENCOUNTER_INFORMATION_LA
from numba_pokemon_prngs.data.personal import PERSONAL_INFO_LA, PersonalInfo8LA
from numba_pokemon_prngs.enums import LATime, LAWeather
from numba_pokemon_prngs.xorshift import Xoroshiro128PlusRejection
from pla_pid_iv.util import (
    ec_pid_const,
    ec_pid_matrix,
    generate_fix_init_spec,
    xoroshiro128plus_next,
)
import pla_pid_iv.pla_reverse.pla_reverse as pla_reverse

from .pa8_reader import ParsedPA8


@dataclass
class RunConfig:
    species_rolls: dict = field(default_factory=dict)  # species_id → shiny_roll_count
    default_rolls: int = 1
    max_gap: int = 4
    max_advances: int = 3000
    save_txt: bool = False

    def get_rolls(self, species_id: int) -> int:
        return self.species_rolls.get(int(species_id), self.default_rolls)


@dataclass
class AdvanceResult:
    advance: int
    species: int
    form: int
    gender: str
    is_alpha: bool
    is_shiny: bool
    level: int
    ivs: tuple  # (HP, Atk, Def, SpA, SpD, Spe)
    ability: int
    nature: str
    height: int
    weight: int
    catch_order: int


def compute_rolls(research_level: int, shiny_charm: bool) -> int:
    """Convert research level (0=Base, 1=Level10, 2=Perfect) + charm to roll count."""
    base = [1, 2, 4][research_level]
    return base + (3 if shiny_charm else 0)


class SeedFinder:
    def __init__(self):
        os.environ["PYOPENCL_COMPILER_OUTPUT"] = "1"
        os.environ.setdefault("PYOPENCL_CTX", "0")
        self.context = cl.create_some_context()
        self.queue = cl.CommandQueue(self.context)

    def find_seeds_for_landmark(
        self,
        pa8: ParsedPA8,
        landmark_data: dict,
        map_index: int,
        config: RunConfig,
        catch_order: int,
        progress_cb: Callable[[str], None],
        result_cb: Callable[[AdvanceResult], None],
    ) -> None:
        activation_rate = landmark_data["activationRate"]
        item_reward_min = landmark_data["itemRewardMin"]
        item_reward_max = landmark_data["itemRewardMax"]
        multiple_unique_items = len(landmark_data["rewardTable"]) > 1
        encounter_table = ENCOUNTER_INFORMATION_LA[map_index + 1][
            np.uint64(landmark_data["encounterTable"])
        ]

        captured_personal_info: PersonalInfo8LA = PERSONAL_INFO_LA[pa8.species]
        if pa8.form:
            captured_personal_info = PERSONAL_INFO_LA[
                captured_personal_info.form_stats_index + pa8.form - 1
            ]

        captured_rolls = config.get_rolls(pa8.species)
        fixed_seed_low = (pa8.encryption_constant - 0x229D6A5B) & 0xFFFFFFFF
        trainer_id = pa8.tid | (pa8.sid << np.uint32(16))

        # --- Fixed seed GPU search ---
        constants = {
            "SHINY_ROLLS": captured_rolls,
            "XORO_CONST": pla_reverse.matrix.vec_to_int(
                ec_pid_const(fixed_seed_low, captured_rolls)
            ),
            "SEED_MAT": ",".join(
                str(pla_reverse.matrix.vec_to_int(row))
                for row in pla_reverse.matrix.generalized_inverse(
                    ec_pid_matrix(captured_rolls)
                )
            ),
            "NULL_SPACE": ",".join(
                str(pla_reverse.matrix.vec_to_int(row))
                for row in pla_reverse.matrix.nullspace(ec_pid_matrix(captured_rolls))
            ),
            "PID": pa8.pid,
            "FIXED_SEED_LOW": fixed_seed_low,
        }
        progress_cb("Searching fixed seeds (GPU)...")
        fixed_seed_program = cl.Program(
            self.context,
            pla_reverse.shaders.build_shader_code("fixed_seed_ec_pid_shader", constants),
        ).build()

        host_results = np.zeros(128, np.uint64)
        host_count = np.zeros(1, np.int32)
        device_results = cl.Buffer(
            self.context,
            cl.mem_flags.WRITE_ONLY | cl.mem_flags.COPY_HOST_PTR,
            hostbuf=host_results,
        )
        device_count = cl.Buffer(
            self.context,
            cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
            hostbuf=host_count,
        )
        fixed_seed_program.find_fixed_seeds(
            self.queue, (2**16,), None, device_count, device_results
        )
        cl.enqueue_copy(self.queue, host_results, device_results)
        cl.enqueue_copy(self.queue, host_count, device_count)
        host_results = host_results[: host_count[0]]

        progress_cb(f"{host_count[0]} candidate fixed seeds, validating...")
        valid_fixed_seeds = []
        for fixed_seed in host_results:
            (_, _, _, ivs, _, _, _, _, _) = generate_fix_init_spec(
                fixed_seed,
                captured_personal_info.gender_ratio,
                captured_rolls,
                False,
                3 if pa8.is_alpha else 0,
                pa8.is_alpha,
                trainer_id,
            )
            if all(iv0 == iv1 for iv0, iv1 in zip(ivs, pa8.ivs)):
                valid_fixed_seeds.append(fixed_seed)

        # --- Landmark seed GPU search ---
        progress_cb(
            f"{len(valid_fixed_seeds)} valid fixed seeds, searching landmark seeds (GPU)..."
        )
        landmark_seeds = []
        for fixed_seed in valid_fixed_seeds:
            for gap in range(2, config.max_gap + 1):
                mat = np.zeros((64, 64), np.uint64)
                seed0, seed1 = np.uint64(0), np.uint64(0x82A2B175229D6A5B)
                for _ in range(gap):
                    seed0, seed1 = xoroshiro128plus_next(seed0, seed1)
                xoro_const = (int(seed0) & 0xFFFFFFFF) | (
                    (int(seed1) & 0xFFFFFFFF) << 32
                )
                for bit in range(64):
                    s0, s1 = np.uint64(1 << bit), np.uint64(0)
                    for _ in range(gap):
                        s0, s1 = xoroshiro128plus_next(s0, s1)
                    for rb in range(32):
                        mat[bit, rb] = (int(s0) >> rb) & 1
                        mat[bit, rb + 32] = (int(s1) >> rb) & 1

                constants = {
                    "SEED_MAT": ",".join(
                        str(pla_reverse.matrix.vec_to_int(row))
                        for row in pla_reverse.matrix.generalized_inverse(mat)
                    ),
                    "NULL_SPACE": ",".join(
                        str(pla_reverse.matrix.vec_to_int(row))
                        for row in pla_reverse.matrix.nullspace(mat)
                    ),
                    "TARGET_RAND": fixed_seed,
                    "GAP": gap,
                    "XORO_CONST": xoro_const,
                }
                ls_program = cl.Program(
                    self.context,
                    pla_reverse.shaders.build_shader_code(
                        "generic_next_64_shader", constants
                    ),
                ).build()
                host_results = np.zeros(128, np.uint64)
                host_count = np.zeros(1, np.int32)
                device_results = cl.Buffer(
                    self.context,
                    cl.mem_flags.WRITE_ONLY | cl.mem_flags.COPY_HOST_PTR,
                    hostbuf=host_results,
                )
                device_count = cl.Buffer(
                    self.context,
                    cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
                    hostbuf=host_count,
                )
                ls_program.find_seeds(
                    self.queue,
                    (2**16, 2**16),
                    None,
                    device_count,
                    device_results,
                )
                cl.enqueue_copy(self.queue, host_results, device_results)
                cl.enqueue_copy(self.queue, host_count, device_count)
                host_results = host_results[: host_count[0]]
                landmark_seeds.extend(
                    (ls, fixed_seed) for ls in host_results
                )

        # --- Validate landmark seeds ---
        progress_cb(
            f"{len(landmark_seeds)} candidate landmark seeds, validating..."
        )
        valid_landmark_seeds = []
        for landmark_seed, fixed_seed in landmark_seeds:
            rng = Xoroshiro128PlusRejection(landmark_seed)
            if rng.next_rand(100) >= activation_rate:
                continue
            rng.next()  # encounter slot
            if fixed_seed != rng.next():
                continue
            valid_landmark_seeds.append(landmark_seed)

        # --- Advance simulation ---
        progress_cb(
            f"{len(valid_landmark_seeds)} valid landmark seeds, simulating advances..."
        )
        identifier = landmark_data.get("identifier", "")

        for landmark_seed in valid_landmark_seeds:
            advance = 0
            rng = Xoroshiro128PlusRejection(0)
            while advance < config.max_advances:
                rng.re_init(landmark_seed)
                has_encounter = rng.next_rand(100) < activation_rate

                if has_encounter:
                    enc_slot = encounter_table.calc_slot(
                        rng.next() * 5.421010862427522e-20,
                        np.int64(LATime.DAY),
                        np.int64(LAWeather.SUNNY),
                    )
                    fixed_seed_adv = rng.next()
                    if enc_slot.min_level != enc_slot.max_level:
                        level = (
                            rng.next_rand(enc_slot.max_level - enc_slot.min_level + 1)
                            + enc_slot.min_level
                        )
                    else:
                        level = enc_slot.min_level

                    slot_species = int(enc_slot.species)
                    slot_personal = PERSONAL_INFO_LA[slot_species]
                    if enc_slot.form:
                        slot_personal = PERSONAL_INFO_LA[
                            slot_personal.form_stats_index + enc_slot.form - 1
                        ]
                    slot_rolls = config.get_rolls(slot_species)

                    (
                        shiny,
                        _,
                        _,
                        ivs,
                        ability,
                        gender_idx,
                        nature_idx,
                        height,
                        weight,
                    ) = generate_fix_init_spec(
                        np.uint64(fixed_seed_adv),
                        slot_personal.gender_ratio,
                        slot_rolls,
                        False,
                        enc_slot.guaranteed_ivs,
                        enc_slot.is_alpha,
                        trainer_id,
                    )

                    result = AdvanceResult(
                        advance=advance,
                        species=slot_species,
                        form=int(enc_slot.form),
                        gender=GENDER_SYMBOLS[gender_idx],
                        is_alpha=bool(enc_slot.is_alpha),
                        is_shiny=bool(shiny),
                        level=int(level),
                        ivs=tuple(int(iv) for iv in ivs),
                        ability=int(ability),
                        nature=NATURES_EN[nature_idx],
                        height=int(height),
                        weight=int(weight),
                        catch_order=catch_order,
                    )
                    result_cb(result)

                # Advance rewards
                if item_reward_min != item_reward_max:
                    reward_count = (
                        rng.next_rand(item_reward_max - item_reward_min + 1)
                        + item_reward_min
                    )
                else:
                    reward_count = item_reward_min
                if has_encounter:
                    reward_count = 10
                for _ in range(reward_count):
                    if multiple_unique_items:
                        rng.next_rand(100)

                landmark_seed = np.uint64(rng.next())
                advance += 1
