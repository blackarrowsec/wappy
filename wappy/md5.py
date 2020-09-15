import hashlib


def get_file_md5(filepath):
    with open(filepath, 'rb') as fi:
        return md5(fi.read())


def md5(content):
    md5_hash = hashlib.md5()
    md5_hash.update(content)
    return md5_hash.hexdigest()
