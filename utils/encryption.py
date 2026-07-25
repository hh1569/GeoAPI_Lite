from passlib.context import CryptContext


# schemes=["bcrypt"]：指定使用 bcrypt 哈希算法（安全性高，带自动加盐）
# deprecated="auto"：自动标记过时/不安全的哈希算法
paw_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hashed_password(password: str):
    return paw_context.hash(password)

##验证明文和密文
def verify_password(plain_password, hashed_password):
    return paw_context.verify(plain_password, hashed_password)

if __name__ == "__main__":
    jj = get_hashed_password('dsadad')
    print(jj)
    print(verify_password('dsadad', jj))