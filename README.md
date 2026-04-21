# landmark-seed-finder

## Pokemon: Legends Arceus landmark (tree/rock) seed finder from a PA8 dumps of pokemon

- Setup for Windows:
	- Go to the link https://git-scm.com/install/windows to install Git
 	- Go to the link https://www.python.org/downloads/windows/ to install Python
  		- Check the box "Add Python to PATH" during installation

- Setup for MacOS:
	- Open your terminal (search for it using `Command-Space` and search 'terminal')
 	- In the terminal, type `bash`
	- Go to the link https://brew.sh/ and install brew using the command (also on the website):

	```/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"```

 	- In the terminal, copy-paste the code:

	```brew install git```

	- Wait for the download to finish. To verify it's installed correctly, type in the terminal:

	```git --version```

	- Then, in the terminal, copy-paste the following code:

	```brew install python```

	- Wait for the download to finish. To verify it's installed correctly, type in the terminal:

	```python3 --version```


- Setup for Linux:
	- Open your terminal and type in the command:

	```sudo apt update```

  	- Then:
 
  	```sudo apt install git -y```

  	- Wait for the download to finish. To verify it's installed, type:
 
  	```git --version```

  	- Then, type in the terminal:

  	```sudo apt install python3 -y```

  	- Wait for the download to finish. To verify it's installed, type:
 
  	```python3 --version```

- Installation of the Landmark Seed Finder:
	- Open your command prompt / terminal
 	- Create a new folder where you want to store the file
 	- Ctrl-C on the folder where you want it installed (e.g. /Users/boombaastical/Documents/landmark_seed_finder)
  	- Go back to your command prompt / terminal and type `cd [directory]`, for example `cd /Users/boombaastical/Documents/landmark_seed_finder`
  	- Then, on the main page of the landmark_seed_finder, and go to the green button written `<> Code` and click on it, and next to the link that appears click the copy icon (the link should be https://github.com/Boombaastical/landmark_seed_finder)
  	- Go back to your command prompt / terminal and type:

	```git clone [Ctrl-V, paste the link you just copied] --recurse-submodules```

	For example, it could look like this:

	```git clone https://github.com/Boombaastical/landmark_seed_finder --recurse-submodules```

	- Wait for the download to finish and then paste this into your terminal:

	```cd landmark_seed_finder```

	- Then, copy-paste the following command in your command prompt / terminal:

   	```git checkout AddedUI```

	- Then, copy-paste the following command in your command prompt / terminal:

	```python main.py```

- Usage:
	- Open the program `using python main.py` (if not already done)
 	- Select the type of landmark you are hunting (Trees, Rocks, Trees and Rocks)
  	- Get on the map you want to hunt the landmark on, and save the game as the map has finished loading
  	- Fly around the map to all the possible landmarks that can be shaking (help yourself with the map from this program)
  	- Every time you see a shaking landmark, find it on the program's map and select it, it will turn green with a number on it
  	- Catch the pokemon that came out of the landmark
  	- Rinse and repeat until you have flown over the area you want to hunt
  	- Talk to the professor to go back to Jubilife Village
  	- Enter an online trade with a bot to gather the pa8 files
 	- Download the pa8 files to a specific folder (e.g. `/Users/boombaastical/Downloads/`)
	- Make sure that the folder selected in the program matches the download folder
 	- Select what type of pokemon you're hunting (shiny and/or alpha)
  	- Select the max number of advances you're willing to make (1 advance = shake a tree, go more than 100m away from it, wait for 20min for it to respawn)
	- Click "Generate"

- Additional information:
	- After clicking "Generate", the program will freeze the selected icons. Press the button "Reset" or press R to reset them
 	- You can change the settings for the search and click "Generate" again.
  	- If you do not click on "Reset", the pa8 files will stay in the download folder. As soon as you click on "Reset", it will move them to the storage folder

- Settings:
	- Max number of advances
 	- Always hunt for shiny pokemon
  	- Always hunt for alpha pokemon
  	- Preset max gap: keep it at 4. If the program doesn't find anything, you can change the max gap between 3 and 7
  	- Save a .txt file of the results when generating: Recommended to always keep it checked, will generate a .txt file with all the pokemon that will appear and at what advances for a specific landmark
  	- Shiny charm: if you have the Shiny Charm or not
  	- Change all to: Allows to directly change all the research level of all the possible pokemon that can appear in landmarks to a certain level
  	- List of species: If your research level differs from each specie, specify it here. Highly recommended to have Perfect Research + Shiny charm for hunting through landmarks
