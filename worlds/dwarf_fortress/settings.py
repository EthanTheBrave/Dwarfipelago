"""
AP host-settings for Dwarf Fortress.

These values are written to the user's host.yaml under the key
"dwarf_fortress_options" and are read at client-launch time.
"""

try:
    from settings import Group, UserFilePath

    class DwarfFortressSettings(Group):
        class GameExecutable(UserFilePath):
            """
            Path to the Dwarf Fortress executable.

            Steam (Windows):  <Steam>\\steamapps\\common\\Dwarf Fortress\\dfhack.exe
            Steam (Linux):    ~/.steam/steam/steamapps/common/Dwarf Fortress/dfhack
            Classic (any OS): path to Dwarf Fortress.exe — install DFHack separately.

            Using dfhack.exe / dfhack is strongly recommended; it launches both
            Dwarf Fortress and DFHack in one step.
            """

            description = "Dwarf Fortress Executable"
            is_exe = True

        game_path: GameExecutable = GameExecutable(
            r"C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress\dfhack.exe"
        )

except ImportError:
    # AP's settings module is not available (e.g. running outside an AP installation).
    # Define a stub so the world can still be imported without errors.
    class DwarfFortressSettings:  # type: ignore[no-redef]
        pass
