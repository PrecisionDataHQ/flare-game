"""Build Flare1.15 from pinned source with isolated SDL and app-private campaign data."""
from pathlib import Path
import os
import re
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[1]
engine=ROOT/'.sources/flare-engine'
game=ROOT/'.sources/flare-game'
revisions=[(engine,'flareteam/flare-engine','v1.15-fdroid','e7c63fa1c3e9033b022cbbf8b23c180806466fa2'),(game,'flareteam/flare-game','v1.15','2ef474f5f5f368628bc526f9e56f936dac743e49')]
for source,repo,tag,revision in revisions:
    if not source.exists():subprocess.run(['git','clone','--depth','1','--branch',tag,'https://github.com/'+repo,str(source)],check=True)
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=revision:
        raise SystemExit('Preserve existing source; use pinned Flare revision: '+revision)
subprocess.run(['git','-C',str(engine),'submodule','update','--init','--recursive','--depth','1'],check=True)
work=ROOT/'build/flare-source';work.mkdir(parents=True,exist_ok=True)
for name in ('src','flare-android-project'):
    shutil.copytree(engine/name,work/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','.gradle','.cxx','build','obj','libs'))
jni=work/'flare-android-project/app/src/main/jni'
names={'SDL2':'joyorbit_flare_sdl2','SDL2_image':'joyorbit_flare_image','SDL2_mixer':'joyorbit_flare_mixer','SDL2_ttf':'joyorbit_flare_ttf','main':'joyorbit_flare_main'}
for p in jni.rglob('Android.mk'):
    lines=[]
    for line in p.read_text().splitlines(keepends=True):
        if re.match(r'\s*LOCAL_(MODULE|SHARED_LIBRARIES|STATIC_LIBRARIES|MODULE_FILENAME)\s*[:+?]?=',line):
            for old,new in names.items():line=re.sub(r'(?<![A-Za-z0-9_])'+re.escape(old)+r'(?![A-Za-z0-9_])',new,line)
        lines.append(line)
    p.write_text(''.join(lines))
for p in (jni/'SDL2').rglob('*'):
    if not p.is_file() or p.suffix not in ('.c','.cpp','.h','.java'):continue
    s=p.read_bytes();new=s.replace(b'org/libsdl/app',b'io/precisiondata/joyorbit/flare/sdl').replace(b'org.libsdl.app',b'io.precisiondata.joyorbit.flare.sdl').replace(b'org_libsdl_app',b'io_precisiondata_joyorbit_flare_sdl')
    if p.suffix=='.java':
        for old,renamed in names.items():new=new.replace(('"'+old+'"').encode(),('"'+renamed+'"').encode())
    if new!=s:p.write_bytes(new)
# Keep all data, settings and saves within this game's private namespace.
p=work/'src/PlatformAndroid.cpp';s=p.read_text();a=s.index('void Platform::setPaths() {');b=s.index('\nvoid Platform::setExitEventFilter()',a)
s=s[:a]+'''void Platform::setPaths() {
    const std::string root = std::string(SDL_AndroidGetInternalStoragePath()) + "/joyorbit/flare/";
    settings->path_data = root + "data/";
    settings->path_user = root + "userdata/";
    settings->path_conf = root + "config/";
    Filesystem::createDir(settings->path_user + "mods");
    Filesystem::createDir(settings->path_user + "saves");
}
'''+s[b:];p.write_text(s)
# The fixed-step loop can run several logic ticks before one render. Retain
# cutscene transitions until render consumes them, rather than losing B/next.
p=work/'src/GameStateCutscene.cpp';s=p.read_text()
s=s.replace('void GameStateCutscene::logic() {', 'void GameStateCutscene::logic() {\n\tif (status != Scene::NO_CHANGE) return;', 1)
s=s.replace('\t\t// process logic() status', '\t\t// process logic() status', 1)
needle='\t\t\tscenes[scene_index]->reset();\n\t\t}\n\t}\n}\n\nbool GameStateCutscene::load'
replacement='\t\t\tscenes[scene_index]->reset();\n\t\t}\n\t\tstatus = Scene::NO_CHANGE;\n\t}\n}\n\nbool GameStateCutscene::load'
if needle not in s:raise SystemExit('Pinned Flare cutscene transition context changed')
s=s.replace(needle,replacement,1);p.write_text(s)
ndk=Path(os.environ.get('JOYORBIT_NATIVE_NDK',str(Path(os.environ['ANDROID_SDK_ROOT'])/'ndk/29.0.14206865')))
project=work/'flare-android-project/app/src/main'
subprocess.run([str(ndk/'ndk-build'),'NDK_PROJECT_PATH='+str(project),'APP_BUILD_SCRIPT='+str(jni/'Android.mk'),'APP_ABI=arm64-v8a','APP_PLATFORM=android-23','APP_MODULES=joyorbit_flare_main','-j6'],check=True)
module=ROOT/'build/flare-embedded';module.mkdir(parents=True,exist_ok=True)
for name in ('gradlew','gradlew.bat'):shutil.copy2(ROOT/'.sources/retroarch/pkg/android/phoenix'/name,module/name)
shutil.copytree(ROOT/'.sources/retroarch/pkg/android/phoenix/gradle',module/'gradle',dirs_exist_ok=True)
(module/'local.properties').write_text('sdk.dir='+os.environ['ANDROID_SDK_ROOT']+'\n')
(module/'gradle.properties').write_text('android.useAndroidX=true\norg.gradle.jvmargs=-Xmx3g\n')
(module/'settings.gradle').write_text('rootProject.name="flare-embedded"\n')
java=module/'java'
shutil.copytree(jni/'SDL2/android-project/app/src/main/java',java,dirs_exist_ok=True)
for p in java.rglob('*.java'):
    s=p.read_text();s=re.sub(r'mContext\.registerReceiver\(([^;]+)\);',r'androidx.core.content.ContextCompat.registerReceiver(mContext, \1, androidx.core.content.ContextCompat.RECEIVER_NOT_EXPORTED);',s);p.write_text(s)
for name in ('JoyOrbitFlareActivity.java','JoyOrbitFlareLaunchActivity.java'):
    target=java/'io/precisiondata/joyorbit/flare'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'android/flare'/name,target)
shutil.copytree(project/'libs',module/'jniLibs',dirs_exist_ok=True)
assets=module/'assets/joyorbit/flare/data';assets.mkdir(parents=True,exist_ok=True)
for parent,name in ((engine,'default'),(game,'fantasycore'),(game,'empyrean_campaign')):
    shutil.copytree(parent/'mods'/name,assets/'mods'/name,dirs_exist_ok=True)
shutil.copy2(engine/'mods/mods.txt',assets/'mods/mods.txt')
shutil.copy2(game/'LICENSE.txt',assets/'Flare-data-CC-BY-SA3.txt')
shutil.copy2(game/'README',assets/'Flare-attribution.txt')
(module/'AndroidManifest.xml').write_text('''<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application>
<activity android:name="io.precisiondata.joyorbit.flare.JoyOrbitFlareLaunchActivity" android:exported="true" android:process=":flareprep" android:screenOrientation="landscape" android:theme="@android:style/Theme.NoTitleBar.Fullscreen"/>
<activity android:name="io.precisiondata.joyorbit.flare.JoyOrbitFlareActivity" android:exported="false" android:process=":flare" android:launchMode="singleInstance" android:screenOrientation="landscape" android:enableOnBackInvokedCallback="false" android:configChanges="orientation|uiMode|screenLayout|screenSize|smallestScreenSize|keyboard|keyboardHidden|navigation" android:theme="@android:style/Theme.NoTitleBar.Fullscreen"/>
</application></manifest>''')
(module/'build.gradle').write_text('''buildscript { repositories { google(); mavenCentral() }; dependencies { classpath 'com.android.tools.build:gradle:9.1.0' } }
repositories { google(); mavenCentral() }
apply plugin: 'com.android.library'
android {
 namespace 'io.precisiondata.joyorbit.flare'
 compileSdk 36
 defaultConfig { minSdk 23 }
 sourceSets { main { manifest.srcFile 'AndroidManifest.xml'; java.srcDirs=['java']; jniLibs.srcDirs=['jniLibs']; assets.srcDirs=['assets'] } }
}
dependencies { implementation 'androidx.core:core:1.17.0' }
''')
subprocess.run(['sh',str(module/'gradlew'),'-p',str(module),'assembleDebug','--no-daemon'],check=True)
out=ROOT/'build/android-apk/libs';out.mkdir(parents=True,exist_ok=True)
shutil.copy2(module/'build/outputs/aar/flare-embedded-debug.aar',out/'joyorbit-flare.aar')
shutil.copy2(engine/'COPYING',ROOT/'theme/licenses/Flare-GPL3.txt')
shutil.copy2(game/'LICENSE.txt',ROOT/'theme/licenses/Flare-data-CC-BY-SA3.txt')
print('Flare source-built and embedded. Runtime/control/save acceptance remains required.')
