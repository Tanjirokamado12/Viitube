# ViiTube,a Youtube on Wii Revival

A Project to Revive Old Youtube App on Wii + old youtube Gdata Apps (from 2011-2014)

# ScreenShots

![HCXPWB_2025-05-29_16-58-18](https://github.com/user-attachments/assets/12888f06-7265-497c-9ae2-e0080ebf97ca)

![HCXPWB_2025-05-29_16-59-50](https://github.com/user-attachments/assets/795dbccf-94db-4156-a07d-fd96f6fb8a3d)

![HCXPWB_2025-05-29_17-00-09](https://github.com/user-attachments/assets/41201252-9b6d-4c9b-9edb-86a9bb58decc)

## Credits

Nintendo and google:For The Channel


What to Watch don't work.I hope a fix is avariable

Most lost of Functionnality works with logon,i will try to get channel working and uploads as offline

If there is amother issue,please post on Issues Part

## Setup 

What you need for Youtube Patch (on wii,no mobile app)

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

Do Click Right and do (Search text) and search for 192.168.1.27

Remplace with your ip

And do that for -Leanbacklite_wii.swf

-apiplayer.swf

-apiplayer-vflZLm5Vu.swf

And Open Leanback_ajax and switch 192.168.1.27 to your ip

## Setup for mobile

You can refer to https://github.com/ftde0/yt2009/blob/main/apk_setup.md ,it works as same way (version 2.0.16 to 4.1.47)

# Reports and Updates

Youtube on Wii

login part:85% done,Just Missing What to Watch and Watch history and Watch later

Playback:100% done.there is not issue (except video take time to load if is the first time to load

Cast:50%,work only on old youtube apps (Gdata only)

Search:50% done,only working as logged on
