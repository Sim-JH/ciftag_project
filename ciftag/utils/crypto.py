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
        encrypt_text = self.cipher_suite.encrypt(plaintext.encode())
        return encrypt_text

    def decrypt_text(self, plaintext):
        if not self.cipher_suite:
            raise ValueError("Cipher suite is not initialized. Generate or load a key first.")
        decrypt_text = self.cipher_suite.decrypt(plaintext).decode()
        return decrypt_text
