from datetime import datetime,timedelta
from jose import jwt
from passlib.context import CryptContext

SECRET_KEY = "SUPER_SECRET_COMPANY_KEY"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")


def create_access_token(data:dict):
    data_copy = data.copy()
    expire_time = datetime.utcnow() + timedelta(hours=24)
    
    data_copy.update({"exp":expire_time})
    
    return jwt.encode(data_copy,SECRET_KEY,algorithm=ALGORITHM)


def verify_token(token:str):
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=ALGORITHM)
        return payload
    except:
        return None

def hash_password(password):
    return pwd_context.hash(password)
    
def verify_password(password,hasedPassword):
    return pwd_context.verify( password,hasedPassword)
    


    
    
    