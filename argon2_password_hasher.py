from argon2 import PasswordHasher, exceptions
import secrets

class Argon2Hasher:
    def __init__(self):
        """
        Recommended Argon2id configuration parameters (2025 standard):
        - time_cost: Number of iterations (CPU cost)
        - memory_cost: Memory usage in KB
        - parallelism: Number of parallel threads
        - hash_len: Hash output length
        - salt_len: Salt length
        """
        self.ph = PasswordHasher(
            time_cost=3,           # Modern hardware: 2-3, older hardware: 1
            memory_cost=65536,     # 64 MB (in KB)
            parallelism=4,         # 4 threads
            hash_len=32,           # 32 bytes = 256 bits
            salt_len=16,           # 16 bytes = 128 bits
        )
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password (automatically generates a random salt)
        Returns format: $argon2id$v=19$m=65536,t=3,p=4$salt$hash
        """
        return self.ph.hash(password)
    
    def verify_password(self, hashed_password: str, password: str) -> bool:
        """
        Verify a password against its hash
        """
        try:
            return self.ph.verify(hashed_password, password)
        except (exceptions.VerifyMismatchError, exceptions.VerificationError):
            return False
    
    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if the password needs to be rehashed (used when parameters are updated)
        """
        return self.ph.check_needs_rehash(hashed_password)

# Usage example
if __name__ == "__main__":
    hasher = Argon2Hasher()
    
    # 1. Hash a password
    password = "Lp324123"  # This is just an example; use a stronger password in production!
    hashed = hasher.hash_password(password)
    print(f"Hashed: {hashed}")
    
    # 2. Verify the password
    test_password = "Lp324123"
    is_valid = hasher.verify_password(hashed, test_password)
    print(f"Password valid: {is_valid}")
    
    # 3. Check if rehashing is needed
    needs_rehash = hasher.needs_rehash(hashed)
    print(f"Needs rehash: {needs_rehash}")