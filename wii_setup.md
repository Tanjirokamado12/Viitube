# ViiTube Setup

A Youtube Mobile and Wii Revival

**
THIS IS NOT ASSOCIATED NOR ENDORSED BY GOOGLE, YOUTUBE, OR NINTENDO
**

Credits:

YouTube/Google/Nintendo (of course)

--

## for the love of all that is holy before contacting me try this

is your wii on the same WIRLESS network as your PC  

did you patch all of the urls

is it all http

are you using WadMII 

are you using the latest version of the YouTube channel


## windows fanboys

https://gist.github.com/aslushnikov/422f1e1a57796a476bf73ebe04f2e5ac (try this for ffmpeg, no I won't compile it for you)

## already have an instance 

  Make Sure to install FFMpeg!

  sudo dnf install ffmpeg

  sudo dnf install libvpx

  

- [1]. once you have your local instance setup, make sure you are using port 80, and your local ip adress, and you're connected to the same network as your wii.

- [2]. grab these programs

  grab a YouTube channel WAD (you can back it up from your wii)
  
  https://github.com/jindrapetrik/jpexs-decompiler
  
  https://www.java.com/en/
  
  https://gbatemp.net/threads/wii-cs-tools-0-3.207472/ (https://code.google.com/archive/p/showmiiwads/downloads)

- [3]. launch JEPXS
 

  open these three files

  (rootofviitube)/swf/apiloader.swf (this loads the real player)

  (rootofviitube)/swf/apiplayer.swf (the real player)

  (rootofviitube)/swf/leanbacklite_wii.swf (this is the app pretty much, this is what the channel loads)

  (rootofviitube)/swf/leanbacklite_v3.swf (this is the TV app pretty much, this is what the TV Client loads)
  
- [4] editing leanback_ajax.json

      Simple, just go into Mobile, fine the file and replace EVERY instance
      of 192.168.1.27 with yours, you can also modify or remove channels and such.
	  Same treatment should be done on all xml on /Mobile directory

- [4]. editing apiloader

   Open Scirpts -> frame 1 -> DoAcition (the first one)
  
   And then simply change any url pointing to 192.168.1.27 to whatever you want.

- [5] editing apiplayer.swf
      
    This is pretty simple replace all instaces of 192.168.1.27 with your url

- [6] editing leanbacklite_wii.swf

    Same procces, just search for all URLs with 192.168.1.27 and replace it with whatever your url is.
  
- [7] extracting the wad

    Use WADMII, and select your wad and extract it to a folder.

- [8] extracting 00000002.app (or whatever, idr its full name)

    Use U8Mii to extract 00000002.app (full name is idr)

- [9] patching wii_shim (or whatever its name) and the wii_dev_shim (or whater its name)

     In trusted folder open wii_shim and wii_dev_shim, change any youtube.com url to your url. (is should be http://%(IP)/wiitv)
	 
     before patching the wad, go to config/common.pcf, scroll all the down until u see "dummy=1", replace that text to "relax=2" and save the pcf, pack the u8 archive and wad

- [10] finishing up

      Finish up packaging, use U8MII to rebuild the 00000002.app (you will have to rename it to .app).
      Then replace 00000002.app from the extracted WAD and rebuild and install it to your wii.
  
- [11]

      Using a private server patcher, patch your wad (like wiimmfi).
