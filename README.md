# landmark-seed-finder

## Pokemon: Legends Arceus landmark (tree/rock) seed finder from a PA8 dumps of pokemon

- Installation:
	- Open your command prompt / terminal
 	- Create a new folder where you want to store the file
 	- Ctrl-C on the folder where you want it installed (e.g. /Users/boombaastical/Documents/landmark_seed_finder)
  	- Go back to your command prompt / terminal and type `cd [directory]`, for example `cd /Users/boombaastical/Documents/landmark_seed_finder`
  	- Then, on the main page of the landmark_seed_finder, and go to the green button written `<> Code` and click on it, and next to the link that appears click the copy icon (the link should be https://github.com/Boombaastical/landmark_seed_finder)
  	- Go back to your command prompt / terminal and type:

```git clone [Ctrl-V, paste the link you just copied] --recurse-submodules```

For example, it could look like this:

```git clone (https://github.com/Boombaastical/landmark_seed_finder) --recurse-submodules```


- Usage:
	- 
 	- Download the pa8 files to a specific folder (folder A)
	- 

		- Map indexes:
			- 0: Obsidian Fieldlands
			- 1: Crimson Mirelands
			- 2: Cobalt Coastlands
			- 3: Coronet Highlands
			- 4: Alabaster Icelands

		- Landmark ID: https://lincoln-lm.github.io/JS-Finder/Gen8/PLA-Landmark-Map/

	- Edit config.toml (text file) to specify the settings to search for each landmark
		- ``shiny_only``
			- Whether or not to filter for shinies (true, false)
		- ``alpha_only``
			- Whether or not to filter for alphas (true, false)
		- ``max_advances``
			- Maximum number of advances to check (integer)
		- ``shiny_rolls``
			- Number of shiny rolls the pokemon generate with (integer)
		- ``max_gap``
			- Maximum gap between landmark & fixed seeds to check (leave at 4 unless you know what youre doing) (integer)
