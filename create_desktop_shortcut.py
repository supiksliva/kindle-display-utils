import os
import subprocess

def make_shortcut():
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    lnk_path = os.path.join(desktop, 'Kindle Studio.lnk')
    target = os.path.abspath(r'C:\Users\Biba\kindle-display-utils\Kindle_GUI.bat')
    work_dir = os.path.abspath(r'C:\Users\Biba\kindle-display-utils')
    
    vbs = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{lnk_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target}"
oLink.WorkingDirectory = "{work_dir}"
oLink.Description = "Kindle Studio - Monitor, Clock, Stream and Canvas"
oLink.IconLocation = "shell32.dll,17"
oLink.Save
'''
    vbs_path = os.path.join(work_dir, '_mklnk.vbs')
    with open(vbs_path, 'w', encoding='utf-8') as f:
        f.write(vbs)
    subprocess.run(['cscript', '//nologo', vbs_path], check=True)
    if os.path.exists(vbs_path):
        os.remove(vbs_path)
    print("Desktop shortcut created:", os.path.exists(lnk_path))

if __name__ == '__main__':
    make_shortcut()
