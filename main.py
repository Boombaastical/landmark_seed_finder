import sys


def _run_cli():
    import glob
    import tomllib

    from core.landmark_loader import MAPS, get_name_en, load_landmark
    from core.pa8_reader import parse_pa8_file
    from core.seed_finder import AdvanceResult, RunConfig, SeedFinder

    def read_pa8_files():
        pa8_files = glob.glob("*.pa8")
        file_info = []
        for file_name in pa8_files:
            catch_number, map_index, id_number = file_name.split("-")
            id_number = id_number.split(".")[0]
            file_info.append((int(catch_number), int(map_index), id_number, file_name))
        return file_info

    def read_config(file_path):
        with open(file_path, "rb") as f:
            return tomllib.load(f)

    config = read_config("config.toml")
    shiny_rolls = config.get("shiny_rolls", 1)
    max_gap = config.get("max_gap", 4)
    look_for_shiny = config.get("shiny_only", True)
    look_for_alpha = config.get("alpha_only", False)
    max_advances = config.get("max_advances", 4000)

    print(
        f"Config info: {shiny_rolls=} {max_gap=} {look_for_shiny=} "
        f"{look_for_alpha=} {max_advances=}"
    )

    run_config = RunConfig(
        species_rolls={},
        default_rolls=shiny_rolls,
        max_gap=max_gap,
        max_advances=max_advances,
        look_for_shiny=look_for_shiny,
        look_for_alpha=look_for_alpha,
        save_txt=True,
    )

    file_info = read_pa8_files()
    finder = SeedFinder()

    for catch_number, map_index, identifier, file_name in file_info:
        print(f"\nProcessing {file_name} (Map: {map_index}, ID: {identifier})")

        landmark_data = load_landmark(map_index, identifier)
        pa8 = parse_pa8_file(file_name)

        print(f"\nProcessing Map: {MAPS[map_index]}")
        print(f"Activation Rate: {landmark_data['activationRate']}%")

        results_for_landmark = []

        def on_result(r: AdvanceResult):
            results_for_landmark.append(r)

        finder.find_seeds_for_landmark(
            pa8, landmark_data, map_index, run_config, catch_number,
            progress_cb=print, result_cb=on_result,
        )

        if results_for_landmark:
            result_file_path = f"{catch_number}-{map_index}-{identifier}-results.txt"
            print(f"Writing results to {result_file_path}")
            with open(result_file_path, "w+", encoding="utf-8") as result_file:
                for r in results_for_landmark:
                    iv_str = "/".join(str(iv) for iv in r.ivs)
                    result_file.write(
                        f"Encounter advance={r.advance}: "
                        f"{get_name_en(r.species, r.form, r.is_alpha)} "
                        f"shiny={r.is_shiny} level={r.level}\n"
                        f"iv_str={iv_str} ability={r.ability} "
                        f"gender={r.gender} nature={r.nature}\n"
                        f"height={r.height}\n"
                        f"weight={r.weight}\n"
                    )
        else:
            print("No matching encounters found in advance range")


if __name__ == "__main__":
    if "--cli" in sys.argv:
        _run_cli()
    else:
        from ui.app import run
        run()
