import binascii
import locale
from pathlib import Path, PureWindowsPath

# ref: https://github.com/bristi/swinlnk
# see also: https://github.com/strayge/pylnk , https://github.com/Matmaus/LnkParse3


class SWinLnk:
    r"""

    Note that all data is passed as strings of numbers (no preceding \x)

    """

    def __init__(self):

        ###############################################################
        # Variables from the official Microsoft documentation
        ###############################################################

        # HeaderSize
        self.HeaderSize = '4c000000'
        # LinkCLSID
        self.LinkCLSID = self.convert_clsid_to_data(
            "00021401-0000-0000-c000-000000000046"
        )
        # HasLinkTargetIDList ForceNoLinkInfo IsUnicode
        self.LinkFlags = '81010000'

        # FILE_ATTRIBUTE_DIRECTORY
        self.FileAttributes_Directory = '10000000'
        # FILE_ATTRIBUTE_ARCHIVE
        self.FileAttributes_File = '20000000'

        self.CreationTime = '0000000000000000'
        self.AccessTime = '0000000000000000'
        self.WriteTime = '0000000000000000'

        self.FileSize = '00000000'
        self.IconIndex = '00000000'
        # SW_SHOWNORMAL
        self.ShowCommand = '01000000'
        # No Hotkey
        self.Hotkey = '0000'
        self.Reserved = '0000'  # Non-modifiable value
        self.Reserved2 = '00000000'  # Non-modifiable value
        self.Reserved3 = '00000000'  # Non-modifiable value
        self.TerminalID = '0000'  # Non-modifiable value

        # Workplace
        self.CLSID_Computer = "20d04fe0-3aea-1069-a2d8-08002b30309d"

        ###############################################################
        # Constants found from file analysis lnk
        ###############################################################

        # Local disk
        self.PREFIX_LOCAL_ROOT = '2f'
        # File folder
        self.PREFIX_FOLDER = '310000000000000000000000'
        # File
        self.PREFIX_FILE = '320000000000000000000000'
        # Root network file server
        self.PREFIX_NETWORK_ROOT = 'c30181'
        # Network printer
        self.PREFIX_NETWORK_PRINTER = 'c302c1'

        self.END_OF_STRING = '00'

        self.cp = locale.getlocale()[1]

    def bytes2hex(self, b):
        return b.hex()

    def gen_idlist(self, id_item):

        # We double length since our input lacks '\x'
        id_item_len = len(id_item) * 2
        item_size = format(int(id_item_len / 4) + 2, '04x')

        slices = [
            (2, 2),
            (0, 2),
        ]

        data = [item_size[x:x + y] for x, y in slices]

        datastring = ''.join(data) + id_item

        # > format(int(72/4)+2, '04x')
        # '0014'

        # When length is used on hex strings like \x00 and we just
        # have 00, then multiply by two ;)

        return datastring

    def convert_clsid_to_data(self, clsid):
        slices = [
            (6, 2),
            (4, 2),
            (2, 2),
            (0, 2),
            (11, 2),
            (9, 2),
            (16, 2),
            (14, 2),
            (19, 4),
            (24, 12),
        ]

        data = [clsid[x:x + y] for x, y in slices]

        datastring = ''.join(data)

        return datastring

    def create_lnk(self, link_target, link_name):
        """

        :param link_target: Eg 'C:\\foo\\bar'
        :param link_name: Eg /home/john/dunno.lnk
        :return:
        """

        root_lnk = False

        target_leaf = ''

        p = PureWindowsPath(link_target)

        prefix_root = self.PREFIX_LOCAL_ROOT
        item_data = '1f50' + \
            self.convert_clsid_to_data(self.CLSID_Computer)
        idlist_items = self.gen_idlist(item_data)  # Root Folder part

        target_root = p.drive

        if len(p.parts) > 1:
            # Leaf is part without drive (and backslash)
            # Eg for 'C:\\Foo\\Bar' we get 'Foo\\Bar'
            target_leaf = str(p)[len(p.drive)+1:]

        if not target_root.endswith('\\'):
            # TODO: Not sure this is a good idea..?
            # log.debug("target_root ends with '\\'")
            target_root += '\\'

        if len(target_leaf) == 0:
            # log.debug("No target leaf so assuming root link")
            root_lnk = True

        # We select the prefix that will be used to display the shortcut icon

        if p.suffix:
            prefix_of_target = self.PREFIX_FILE
            file_attributes = self.FileAttributes_File
        else:
            prefix_of_target = self.PREFIX_FOLDER
            file_attributes = self.FileAttributes_Directory

        # Convert target values to binary
        # print('target_root: {}'.format(target_root))
        # print('target_leaf: {}'.format(target_leaf))

        target_root = self.bytes2hex(target_root.encode(self.cp))
        # Needed from Vista and higher otherwise the link is considered
        # empty (I have not found any information about this)
        target_root = target_root + ('00' * 21)

        # Create the IDLIST that represents the core of the LNK file

        # Volume Item part
        idlist_items += self.gen_idlist(
            prefix_root + target_root + self.END_OF_STRING
        )

        # File entry parts
        if not root_lnk:
            items = [self.bytes2hex(x.encode(self.cp)) for x in p.parts[1:]]
            for item in items[:-1]:
                data = self.PREFIX_FOLDER + item + self.END_OF_STRING
                idlist_items += self.gen_idlist(data)

            data = prefix_of_target + items[-1] + self.END_OF_STRING
            idlist_items += self.gen_idlist(data)

        idlist = self.gen_idlist(idlist_items)

        with open(link_name, 'wb') as fout:
            fout.write(
                binascii.unhexlify(''.join([
                    self.HeaderSize,
                    self.LinkCLSID,
                    self.LinkFlags,
                    file_attributes,
                    self.CreationTime,
                    self.AccessTime,
                    self.WriteTime,
                    self.FileSize,
                    self.IconIndex,
                    self.ShowCommand,
                    self.Hotkey,
                    self.Reserved,
                    self.Reserved2,
                    self.Reserved3,
                    idlist,
                    self.TerminalID,
                ]))
            )


def create_lnk(link_target, link_name):
    swl = SWinLnk()
    link_target = Path(link_target).absolute()
    swl.create_lnk(link_target, link_name)
