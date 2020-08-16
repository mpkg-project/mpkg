# mpkg

mpkg 主要用于下载最新的软件，对安装软件的支持不佳，默认非静默安装。

## Demo

```bash
#pip install mpkg
pip install git+https://github.com/mpkg-project/mpkg.git
mpkg set sources --add https://github.com/mpkg-project/mpkg-autobuild/releases/download/AutoBuild/main.json.latest
mpkg sync

mpkg list -A
# ['7zip', 'IntelWirelessDriver.admin', 'TrafficMonitor.install', ...]
mpkg list 7zip
mpkg install 7zip
```

## 说明

初次使用时执行`mpkg config`设置软件源，也可通过`mpkg set --add sources "url"`进行设置。

软件源以扩展名分为 .json, .py, .zip, .sources 四类。py 源类似爬虫，用于获取软件信息，而软件信息都可以表示为 json 源的形式。通过 zip 源与 sources 源可以处理多个 py 源与 json 源。非 json 源需要执行`mpkg set unsafe yes`以启用。

软件源地址若以 http 开头，则会同时请求 `文件名.ver` 文件判断有无更新（sources 源除外）。若不以 http 开头则识别为本地路径（建议使用绝对路径），不读取 .ver 文件，直接加载本地文件。在软件源地址后加 .latest 可跳过 .ver 文件的获取。

`mpkg sync`会同步所有软件源并显示有无更新。`mpkg list -A`显示软件源中所有软件的 name 值。`mpkg list example`显示软件详细信息，`mpkg install example`会下载软件并保存版本号等信息，然后直接运行 exe 文件。`mpkg download example`仅下载软件，且不保留安装信息。
