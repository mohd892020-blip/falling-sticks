"""Build the offline Android app (APK to install directly + AAB for Google Play) without Gradle.

Usage:  python android/build.py
Needs the Android SDK, a JDK and bundletool. By default they come from the Unity 6 install on this PC;
override with the env vars ANDROID_SDK, JAVA_HOME and BUNDLETOOL.
Signing details are read from android/signing.properties (git-ignored; see README.md).
Output: android/out/FallingSticks-<version>.apk and .aab
"""
import io, os, re, shutil, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UNITY = r'C:\Program Files\Unity\Hub\Editor\6000.3.27f2\Editor\Data\PlaybackEngines\AndroidPlayer'
SDK = os.environ.get('ANDROID_SDK') or os.path.join(UNITY, 'SDK')
JDK = os.environ.get('JAVA_HOME') or os.path.join(UNITY, 'OpenJDK')
BUNDLETOOL = os.environ.get('BUNDLETOOL') or os.path.join(UNITY, 'Tools', 'bundletool-all-1.17.2.jar')
BT = os.path.join(SDK, 'build-tools', sorted(os.listdir(os.path.join(SDK, 'build-tools')))[-1])
TARGET = 35
ANDROID_JAR = os.path.join(SDK, 'platforms', 'android-%d' % TARGET, 'android.jar')
MIN_SDK = 24
WEB_FILES = ['index.html', 'manifest.webmanifest']          # plus the folders below
WEB_DIRS = ['icons', 'fonts']
BUILD = tempfile.mkdtemp(prefix='fallingsticks-android-')   # a fresh folder outside the synced project
OUT = os.path.join(HERE, 'out')
ENV = dict(os.environ, JAVA_HOME=JDK, PATH=os.path.join(JDK, 'bin') + os.pathsep + os.environ.get('PATH', ''))


def run(*cmd, quiet=False):
    r = subprocess.run([str(c) for c in cmd], env=ENV, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:]); sys.exit('FAILED: ' + os.path.basename(str(cmd[0])))
    if not quiet and r.stdout.strip(): print(r.stdout.strip()[-1500:])
    return r


def tool(name):
    for ext in ('', '.exe', '.bat'):
        p = os.path.join(BT, name + ext)
        if os.path.exists(p): return p
    sys.exit('missing build tool: ' + name)


def signing():
    p = os.path.join(HERE, 'signing.properties')
    if not os.path.exists(p): sys.exit('android/signing.properties is missing (see android/README.md)')
    d = dict(l.split('=', 1) for l in io.open(p, encoding='utf-8-sig').read().splitlines() if '=' in l)
    return {k.strip(): v.strip() for k, v in d.items()}


def version():
    v = re.search(r"const VERSION = '([\d.]+)'", io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()).group(1)
    a, b, c = (list(map(int, v.split('.'))) + [0, 0])[:3]
    return v, a * 10000 + b * 100 + c                          # 2.10.0 → 21000


def main():
    vname, vcode = version()
    print('Falling Sticks %s (versionCode %d), target SDK %d' % (vname, vcode, TARGET))
    os.makedirs(OUT, exist_ok=True)

    www = os.path.join(BUILD, 'assets', 'www')                 # 1. the game files
    os.makedirs(www)
    for f in WEB_FILES: shutil.copy(os.path.join(ROOT, f), www)
    for d in WEB_DIRS: shutil.copytree(os.path.join(ROOT, d), os.path.join(www, d))

    aapt2 = tool('aapt2')                                       # 2. resources + manifest
    run(aapt2, 'compile', '--dir', os.path.join(HERE, 'res'), '-o', os.path.join(BUILD, 'res.zip'))
    link = [aapt2, 'link', '-I', ANDROID_JAR, '--manifest', os.path.join(HERE, 'AndroidManifest.xml'), os.path.join(BUILD, 'res.zip'),
            '-A', os.path.join(BUILD, 'assets'), '--min-sdk-version', MIN_SDK, '--target-sdk-version', TARGET,
            '--version-code', vcode, '--version-name', vname, '--auto-add-overlay']
    run(*link, '-o', os.path.join(BUILD, 'res.apk'))
    run(*link, '--proto-format', '-o', os.path.join(BUILD, 'proto.apk'))

    classes = os.path.join(BUILD, 'classes')                   # 3. code
    srcs = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(HERE, 'src')) for f in fs if f.endswith('.java')]
    run(os.path.join(JDK, 'bin', 'javac'), '-encoding', 'UTF-8', '-source', '8', '-target', '8', '-Xlint:-options',
        '-bootclasspath', ANDROID_JAR, '-d', classes, *srcs, quiet=True)
    dex = os.path.join(BUILD, 'dex'); os.makedirs(dex)
    cls = [os.path.join(dp, f) for dp, _, fs in os.walk(classes) for f in fs if f.endswith('.class')]
    run(tool('d8'), '--release', '--min-api', MIN_SDK, '--lib', ANDROID_JAR, '--output', dex, *cls)

    s = signing()
    ENV['FS_KS_PASS'], ENV['FS_KEY_PASS'] = s['storePassword'], s['keyPassword']
    base = 'FallingSticks-%s' % vname

    unsigned = os.path.join(BUILD, 'unsigned.apk')             # 4. APK: add dex, align, sign
    shutil.copy(os.path.join(BUILD, 'res.apk'), unsigned)
    with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as z: z.write(os.path.join(dex, 'classes.dex'), 'classes.dex')
    aligned = os.path.join(BUILD, 'aligned.apk')
    run(tool('zipalign'), '-f', '-p', '4', unsigned, aligned)
    apk = os.path.join(OUT, base + '.apk')
    run(tool('apksigner'), 'sign', '--ks', s['storeFile'], '--ks-key-alias', s['keyAlias'], '--ks-pass', 'env:FS_KS_PASS',
        '--key-pass', 'env:FS_KEY_PASS', '--out', apk, aligned)
    run(tool('apksigner'), 'verify', '--min-sdk-version', MIN_SDK, apk)

    module = os.path.join(BUILD, 'base.zip')                   # 5. AAB: proto resources in bundle layout, then bundletool + jarsigner
    with zipfile.ZipFile(os.path.join(BUILD, 'proto.apk')) as src, zipfile.ZipFile(module, 'w', zipfile.ZIP_DEFLATED) as z:
        for it in src.infolist():
            n = it.filename
            dst = 'manifest/AndroidManifest.xml' if n == 'AndroidManifest.xml' else n   # res/, assets/, resources.pb stay as they are
            z.writestr(dst, src.read(n))
        z.write(os.path.join(dex, 'classes.dex'), 'dex/classes.dex')
    aab = os.path.join(OUT, base + '.aab')
    if os.path.exists(aab): os.remove(aab)
    java = os.path.join(JDK, 'bin', 'java')
    run(java, '-jar', BUNDLETOOL, 'build-bundle', '--modules=' + module, '--output=' + aab)
    run(os.path.join(JDK, 'bin', 'jarsigner'), '-keystore', s['storeFile'], '-storepass:env', 'FS_KS_PASS', '-keypass:env', 'FS_KEY_PASS',
        '-sigalg', 'SHA256withRSA', '-digestalg', 'SHA-256', aab, s['keyAlias'], quiet=True)
    run(java, '-jar', BUNDLETOOL, 'validate', '--bundle=' + aab, quiet=True)
    for f in (apk, aab): print('%-40s %6.0f KB' % (os.path.basename(f), os.path.getsize(f) / 1024))
    shutil.rmtree(BUILD, ignore_errors=True)


if __name__ == '__main__':
    main()
