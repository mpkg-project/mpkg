# mpkg

[![PyPI status](https://img.shields.io/pypi/status/mpkg.svg)](https://pypi.org/project/mpkg/)
[![GitHub release](https://img.shields.io/github/release/mpkg-project/mpkg.svg)](https://GitHub.com/mpkg-project/mpkg/releases/)
[![Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://pypi.org/project/mpkg/)

mpkg 主要用于获取最新的软件。

mpkg 可以通过一个 json 文件保存大量软件信息，也可以调用 python 代码爬取信息。软件信息可以通过同步 json 或通过本地爬取获得，信息同步完成后可在本地查看、搜索或下载软件，不需要调用其他网站的 api。

mpkg 下载软件时不需要管理员权限，调用可执行文件进行安装时可能需要权限，调用时默认不附加静默安装参数。

灵感主要来源于以下项目：

- [Scoop](https://github.com/lukesampson/scoop)

- [chocolatey](https://chocolatey.org/)

## Demo

```bash
# pip install mpkg
pip install --upgrade https://github.com/mpkg-project/mpkg/archive/master.zip

mpkg doctor --add-repo main
# 即 mpkg set sources --add https://github.com/mpkg-bot/mpkg-history/raw/master/main.json

# mpkg set sources --add https://github.com/mpkg-bot/mpkg-history/raw/master/scoop.json
# mpkg set sources --add https://github.com/mpkg-bot/mpkg-history/raw/master/winget.json

mpkg sync

mpkg doctor

mpkg show -A --pprint
# ['7zip', 'IntelWirelessDriver.admin', 'TrafficMonitor.install', ...]
mpkg show 7zip
mpkg install 7zip
mpkg download mpkg.download --root .
```

## 安装

如果已安装 python3.7（或更高版本），执行 `pip install mpkg` 即可安装。[Releases](https://github.com/mpkg-project/mpkg/releases) 页面提供了用 pyinstaller 打包好的程序，但可能有未知 bug。

如果想尝试最新版本，可通过 `pip install --upgrade https://github.com/mpkg-project/mpkg/archive/master.zip` 安装 git 仓库中的版本（可能需要先运行 `pip uninstall mpkg` 卸载旧版本），且对应的已打包程序可在 [此处](https://ci.appveyor.com/project/zpcc/mpkg/) 找到。

## 配置

初次使用时执行`mpkg config`设置软件源，也可通过`mpkg set --add sources "url"`或`mpkg doctor --add-repo repo_name`进行设置。

软件源以扩展名分为 .json, .py, .zip, .sources 四类。py 源类似爬虫，用于获取软件信息，而软件信息都可以表示为 json 源的形式。通过 zip 源与 sources 源可以处理多个 py 源与 json 源。非 json 源需要执行`mpkg set unsafe yes`以启用。

`mpkg sync`会同步所有软件源并显示有无更新。`mpkg show -A`显示软件源中所有软件的 name 值。`mpkg show example`显示软件详细信息，`mpkg install example`会下载软件并保存版本号等信息，然后直接运行 exe 文件。`mpkg download example`仅下载软件，且不保留安装信息。

注意，安装过程中出现 warning 仍视为安装成功。

### 软件信息示例

```python
[{'args': '/S', # 可选，mpkg install 加入 --quiet(-q) 选项后会在调用安装包时追加此字符串
  'changelog': 'https://nmap.org/changelog.html',
  # 可选，mpkg sync 加入 --changelog(-l) 选项后会在软件包有更新时同时显示此字符串
  'id': 'nmap', # 必须存在，且保证软件源中 id 不重复
  'links': ['https://nmap.org/dist/nmap-7.80-setup.exe'],
  # links 与 arch 必选其一，不能共存，在下载过程中使用
  # 且下载过程中只会下载一个链接，若 links 有多项则会要求用户进行选择
  'name': 'nmap', # 可选，程序通过 name 值区分软件，此键会根据 id 自动生成
  'ver': '7.80' # 必须存在，且为字符串
  }]
[{'arch': {'32bit': 'https://github.com/zhongyang219/TrafficMonitor/releases/download/V1.79.1/TrafficMonitor_V1.79.1_x86.7z',
           '64bit': 'https://github.com/zhongyang219/TrafficMonitor/releases/download/V1.79.1/TrafficMonitor_V1.79.1_x64.7z'},
  'bin': ['MPKG-PORTABLE'], # 可选，存在此键时软件会识别为 portable 类型，并自动解压下载后的安装包
  # MPKG-PORTABLE 用于占位，若为其他值，则会生成调用命令
  'cmd': {'end': 'cd /d "{root}" && start TrafficMonitor.exe',
          'start': 'taskkill /im TrafficMonitor.exe /t >nul'},
  # 可选，在程序安装前后调用
  'id': 'TrafficMonitor.install',
  'ver': '1.79.1'}]
# 参见：https://github.com/mpkg-bot/mpkg-history/tree/master/main
```

### 重要选项

#### mpkg set allow_portable yes

若软件为 portable 类型（如 wget，无安装包），需要安装 7zip 并执行`mpkg set allow_portable yes`，否则会出现类似`skip portable ...`的 warning。此外，wget 等软件会生成调用命令，同时需要修改环境变量（运行 `mpkg doctor --fix-bin-env`）。

注意，mpkg 会调用`C:\Program Files\7-Zip\7z.exe`解压压缩包。若 7z 安装位置有误，可尝试运行`mpkg doctor --fix-7z-path`，也可手动设置（如`mpkg set 7z "\"C:\Program Files (x86)\7-Zip\7z.exe\" x {filepath} -o{root} -aoa > nul"`）。

#### mpkg set shimexe "path"

为方便在命令行中调用程序，mpkg 需要手动将 `%USERPROFILE%\.config\mpkg\bin` 目录加入至环境变量 PATH 中（也可通过 `mpkg set bin_dir dir` 修改目录位置）。mpkg 默认会根据软件信息通过创建 bat 的方式调用命令（如调用 curl, wget, adb 等），若设置 shimexe，则会生成 exe 来进行调用而非通过 bat。建议设置该项（运行 `mpkg install shimexe_kiennq`）。

注意，该选项仅用于 Windows，Linux 系统使用 `ln -s` 实现此效果。

#### mpkg set allow_cmd yes

若软件需要调用 cmd 命令（如 TrafficMonitor.install），则需要执行`mpkg set allow_cmd yes`，否则会输出`skip command(...)`。在调用 cmd 命令时会要求输入 y 进行确认，可通过执行 `mpkg set no_confirmation yes` 跳过确认。

### 杂项

```bash
mpkg set debug yes
# 执行后会显示加载软件源、页面请求等信息

mpkg set download_cache yes
# 执行后，若下载文件所在目录存在文件名后加 .cached 的文件，则跳过该文件的下载

mpkg set download_resuming yes
# 执行后，若所下载文件大于 20MB，则启用续传功能

mpkg set delete_after_install yes
# 执行后，在安装完软件后会删除安装包

mpkg set proxy username:password@https://example.com:8081
mpkg set proxy http://127.0.0.1:1081
# 执行后会使用代理进行页面请求与软件下载，仅支持http与https代理

mpkg set redirect --add --dict "^https?://github.com/(.*)/raw/master/(.*)" https://cdn.jsdelivr.net/gh/{0}@master/{1}
# 执行后，进行页面请求与软件下载会重定向网站，语法同正则表达式

mpkg set saveto --add --dict ".msi" "TEMPDIR-D"
# 执行后，后缀为 .msi 的文件在下载时会保存至所输入目录，TEMPDIR-D 代表自动生成一个临时目录，且在安装后删除，输入 TEMPDIR 则不自动删除

mpkg set UA "..."
# 执行后，进行页面请求与软件下载时会使用此UA。修改后可能出问题，使用 mpkg set UA --delete 还原

mpkg set timeout 6
# 执行后，请求超时时间修改为6秒（默认为5秒）

mpkg set retry_attempts 5
# 执行后，请求失败后重试次数修改为5次（默认为3）

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

mpkg set --name name string
# 用 string 替换 name，可以用于简化命名
```

## Special Thanks

Thank you to [JetBrains](https://www.jetbrains.com/) for providing us with free licenses to their great tools.
