import base64
from cryptography.fernet import Fernet


class CiftagCrypto:
    def __init__(self):
        self.cipher_suite = None

    def key_gen(self):
        key = Fernet.generate_key()
        return key

    def load_key(self, key):
        self.cipher_suite = Fernet(key)

    def encrypt_text(self, plaintext):
        if not self.cipher_suite:
            raise ValueError("Cipher suite is not initialized. Generate or load a key first.")
        encrypt_bytes = self.cipher_suite.encrypt(plaintext.encode())
        encrypt_text = self.base64_covert(encrypt_bytes)
        return encrypt_text

    def decrypt_text(self, encrypt_text):
        if not self.cipher_suite:
            raise ValueError("Cipher suite is not initialized. Generate or load a key first.")
        encrypt_bytes = self.base64_covert(encrypt_text.encode('utf-8'), 'decode')
        decrypt_text = self.cipher_suite.decrypt(encrypt_bytes).decode()
        return decrypt_text

    @staticmethod
    def base64_covert(text, trans='encode'):
        if trans == 'encode':
            return base64.urlsafe_b64encode(text).decode('utf-8')
        else:
            return base64.urlsafe_b64decode(text)