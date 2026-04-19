import glob
import os
from dataclasses import dataclass

import numpy as np

from pla_pid_iv.util.pa8 import PA8


@dataclass
class ParsedPA8:
    species: int
    form: int
    pid: int
    encryption_constant: int
    tid: int
    sid: int
    iv32: int
    is_alpha: bool
    ivs: tuple  # (HP, Atk, Def, SpA, SpD, Spe)


def parse_pa8_file(path: str) -> ParsedPA8:
    mon = np.fromfile(path, dtype=PA8.dtype).view(np.recarray)[0]
    ivs = (
        int(mon.iv32 & 0x1F),
        int((mon.iv32 >> 5) & 0x1F),
        int((mon.iv32 >> 10) & 0x1F),
        int((mon.iv32 >> 20) & 0x1F),
        int((mon.iv32 >> 25) & 0x1F),
        int((mon.iv32 >> 15) & 0x1F),
    )
    return ParsedPA8(
        species=int(mon.species),
        form=int(mon.form),
        pid=int(mon.pid),
        encryption_constant=int(mon.encryption_constant),
        tid=int(mon.tid),
        sid=int(mon.sid),
        iv32=int(mon.iv32),
        is_alpha=bool(mon._16 & 32),
        ivs=ivs,
    )


def read_pa8_files_from_folder(folder: str) -> list[str]:
    """Return all .pa8 files in folder sorted by creation time (oldest first)."""
    pa8_files = glob.glob(os.path.join(folder, "*.pa8"))
    pa8_files.sort(key=lambda f: os.path.getctime(f))
    return pa8_files
