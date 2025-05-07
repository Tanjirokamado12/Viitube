# ViiTube,a Youtube on Wii Revival

**
THIS IS NOT ASSOCIATED NOR ENDORSED BY GOOGLE, YOUTUBE, OR NINTENDO AND LIINBACK
**

--

This Revival has been add With Vii no ma revial,But Removed and Converted to python due to Issue With Video Downloading and converting,so this tutorial can have errors

--

Installation 

 
  You Need:
  
  -a YouTube channel WAD (you can back it up from your wii)
  
  -Jpexs Decompiller:https://github.com/jindrapetrik/jpexs-decompiler
  
  -Java (for JPEXS):https://www.java.com/en/
  
  -Wii C.s tools (for unpack and repack) https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/showmiiwads/Wii.cs%20Tools%200.3.rar (extract it)

  -FFMPEG (required to get Video Playback) https://www.ffmpeg.org/download.html

  -Python (For get a working server) https://www.python.org/downloads/windows/

1.Patch The Wad

With WadMii of Wii c.s tools,extract the Wad and with U8mii Extract 00000002.app

After go to 00000002.app_OUT/Trusted

Launch JPEXS and Open wii_shim.swf and wii_dev_shim.swf

Do Click Right and do (Search text) and search for www.youtube.com

You will see /wiitv and /s/tv/config/ remplace / to http:// your ipv4/ ,do this on wii_shim.swf and wii_dev_shim.swf and save it

If you want your IPV4 (on Windows)

Do Windows+R and Type CMD and do Ctrl Shift Enter

Do yes and type IPconfig

Search IPV6 adress (is should be 192.168.1.xxx)

After open on notepad 00000002.app_OUT/config/common.pcf and remplace dummy=1 to relax=2

Repack with u8it 00000002.app and wad with wadmii

And for End Wad Patch,is required to patch the wad with wimmifi patcher

2:Patch Channel Files

From ytwii of this repo,open on JPEXS

-Leanbacklite_wii.swf

-apiplayer.swf

-apiplayer-vflZLm5Vu.swf

-leanback_ajax (should be opened on a Text Editor)

Operation to do with all swf files

Do Click Right and do (Search text) and search for 192.168.1.18

Remplace with your ip 

And do that for 
-Leanbacklite_wii.swf

-apiplayer.swf

-apiplayer-vflZLm5Vu.swf

And Open Leanback_ajax and switch 192.168.1.18 to your ip

After you can save it And is Patched (if you have a issue,you can go to https://discord.gg/K8z8rzWnvt for help,i try to respond as soon as i can)
