# mpkg

mpkg 主要用于下载最新的软件，对安装软件的支持不佳，默认非静默安装。

## Demo

```bash
#pip install mpkg
pip install git+https://github.com/mpkg-project/mpkg.git
mpkg set sources --add https://github.com/mpkg-project/mpkg-autobuild/releases/download/AutoBuild/main.json.latest
mpkg sync

mpkg show -A
# ['7zip', 'IntelWirelessDriver.admin', 'TrafficMonitor.install', ...]
mpkg show 7zip
mpkg install 7zip
```

## 说明

初次使用时执行`mpkg config`设置软件源，也可通过`mpkg set --add sources "url"`进行设置。

软件源以扩展名分为 .json, .py, .zip, .sources 四类。py 源类似爬虫，用于获取软件信息，而软件信息都可以表示为 json 源的形式。通过 zip 源与 sources 源可以处理多个 py 源与 json 源。非 json 源需要执行`mpkg set unsafe yes`以启用。

软件源地址若以 http 开头，则会同时请求 `文件名.ver` 文件判断有无更新（sources 源除外）。若不以 http 开头则识别为本地路径（建议使用绝对路径），不读取 .ver 文件，直接加载本地文件。在软件源地址后加 .latest 可跳过 .ver 文件的获取。

`mpkg sync`会同步所有软件源并显示有无更新。`mpkg list -A`显示软件源中所有软件的 name 值。`mpkg show example`显示软件详细信息，`mpkg install example`会下载软件并保存版本号等信息，然后直接运行 exe 文件。`mpkg download example`仅下载软件，且不保留安装信息。

注意，安装过程中出现 warning 仍视为安装成功。

### 重要选项

#### mpkg set allow_portable yes

若软件无安装包（如 TrafficMonitor.portable），需要安装 7zip 并执行`mpkg set allow_portable yes`，否则会出现类似`skip portable ...`的 warning。

注意，若软件信息中包含 bin 字段，则视为无安装包的 portable 类型。mpkg 会调用`C:\Program Files\7-Zip\7z.exe`解压压缩包。若 7z 安装位置有误，可进行手动设置（如`mpkg set 7z "\"C:\Program Files (x86)\7-Zip\7z.exe\" x {filepath} -o{root} -aoa > nul"`）。

#### mpkg set allow_cmd yes

若软件需要调用 cmd 命令（如 TrafficMonitor.install），则需要执行`mpkg set allow_cmd yes`，否则会输出`skip command(...)`。在调用 cmd 命令时会要求输入 y 进行确认，可通过执行`mpkg set skip_confirm yes`跳过。

#### mpkg set shortcut_command ...

mpkg 不支持创建快捷方式，但可通过调用命令的方式实现。若未设置此项，需要创建快捷方式时会出现`no shortcut for ...`的 warning，下面给出一种调用示例（若无特殊情况，快捷方式一般只需创建一次，因而也可手动创建快捷方式并忽略此设置）。

```cmd
rem 需要修改 C:\DESKTOP 为桌面文件夹所在路径
mpkg set shortcut_command "mshta VBScript:Execute(\"Set a=CreateObject(\"\"WScript.Shell\"\"):Set b=a.CreateShortcut(\"\"C:\DESKTOP\{name}.lnk\"\"):b.TargetPath=\"\"{target}\"\":b.Arguments =\"\"{args}\"\":b.WorkingDirectory=\"\"{root}\"\":b.Save:close\")"
```

#### mpkg set link_command ...

mpkg 可以通过创建 bat 的方式调用命令（如 curl, wget, adb 等），但需要手动加入`%USERPROFILE%\.config\mpkg\bin`至 PATH 环境变量中。可以忽略对 link_command 的设置。

### 杂项

```bash
mpkg set debug yes
# 执行后会显示加载软件源、页面请求等信息

mpkg set download_cache yes
# 执行后，若下载文件所在目录存在文件名后加 .cached 的文件，则跳过该文件的下载

mpkg set proxy username:password@https://example.com:8081
mpkg set proxy http://127.0.0.1:1081
# 执行后会使用代理进行页面请求与软件下载，仅支持http与https代理

mpkg set redirect --add --dict "^https?://github.com/(.*)/raw/master/(.*)" https://cdn.jsdelivr.net/gh/{0}@master/{1}
# 执行后，进行页面请求与软件下载会重定向网站，语法同正则表达式

mpkg set UA "..."
# 执行后，进行页面请求与软件下载会使用此UA

mpkg set timeout 6
# 执行后，页面请求超时时间修改为6秒（默认为5秒）

mpkg set files_dir ...
# portable 类型的软件会解压至此目录，默认为 %USERPROFILE%\.config\mpkg\files
# 建议仅在初次使用 mpkg 时修改此目录

mpkg set download_dir ...
# 软件会下载至此目录，默认为 %USERPROFILE%\.config\mpkg\Downloads

mpkg set bin_dir ...
# 需要确保此目录在 PATH 中

mpkg set --notes id string
# 若该 id 所对应软件在 sync 后找到更新，则会同时显示 string

mpkg set --root id dir
# 该 id 所对应的 portable 软件在 install 时会解压至 dir

mpkg set --args id string
# 该 id 所对应的软件在 install -q 时会使用此参数
```
