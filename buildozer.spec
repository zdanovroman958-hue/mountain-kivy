[app]

title = Горный байкер
package.name = gornyybayker
package.domain = com.multitool

source.dir = .
source.include_exts = py,png,ttf,otf
source.exclude_dirs = __pycache__, .git, .github, .buildozer

version = 1.0.0

requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0

orientation = landscape
fullscreen = 1
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.console = 0
android.logcat = 1

[buildozer]

log_level = 2
warn_on_root = 1
build_dir = ./.buildozer
bin_dir = ./bin