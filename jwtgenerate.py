import jwt
from datetime import datetime, timedelta

class JWT_Token():
    
    secret_key = '2889b2b99b0235aff49c4246e857fd7396cc88fd1b38718b1f4d8de6807fa95b'
    algorithm = "HS256"

    def generate_token(self, user_id, role, name, user_name,level):
        token_exp = datetime.utcnow() + timedelta(days=31)
        secret_key = self.secret_key
        token = jwt.encode({'user_id': user_id, 'role': role,"name":name, "level":level,'user_name': user_name, 'exp': token_exp}, secret_key, algorithm=self.algorithm)

        return token
    def generate_token_teacher(self, user_id, role, name, user_name):
        token_exp = datetime.utcnow() + timedelta(days=31)
        secret_key = self.secret_key
        token = jwt.encode({'user_id': user_id, 'role': role,"name":name, 'user_name': user_name, 'exp': token_exp}, secret_key, algorithm=self.algorithm)

        return token


    def verify_token(self, token):
        decoded_token = self.decode_token(token)
        if decoded_token is None:
            return False
        else:
            return True

    def decode_token(self, token):
        msg = ""
        secret_key = self.secret_key
        algorithm = self.algorithm

        try:
            decoded_token = jwt.decode(token, secret_key, algorithms=[algorithm])
            return decoded_token,msg
        except jwt.ExpiredSignatureError:
            msg = 'Token has expired'
            return msg
        except jwt.InvalidSignatureError:
            msg = 'Token has invalid signature'
            return msg
        except jwt.DecodeError:
            msg = 'Error decoding token'
            return msg

   
if __name__ == "__main__":
        
    jwt_handler = JWT_Token()
    tokens = jwt_handler.generate_token("user123", "admin", "John", "Doe", "john@example.com")
    print("Access Token:", tokens['access_token'])
    print("Refresh Token:", tokens['refresh_token'])

    # Yenileme tokeni ile erişim tokenini yenileme
    new_access_token = jwt_handler.refresh_access_token(tokens['refresh_token'])
    if new_access_token:
        print("New Access Token:", new_access_token['access_token'])
    else:
        print("Access Token could not be refreshed")
