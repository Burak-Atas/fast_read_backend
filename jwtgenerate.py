import jwt
import config
from datetime import datetime, timedelta, timezone

TOKEN_LIFETIME = timedelta(days=31)


class JWT_Token():

    secret_key = config.SECRET_KEY
    algorithm = "HS256"

    def generate_token(self, user_id, role, name, user_name, level):
        token_exp = datetime.now(timezone.utc) + TOKEN_LIFETIME
        token = jwt.encode({'user_id': user_id, 'role': role, "name": name, "level": level, 'user_name': user_name, 'exp': token_exp}, self.secret_key, algorithm=self.algorithm)
        return token

    def generate_token_teacher(self, user_id, role, name, user_name):
        token_exp = datetime.now(timezone.utc) + TOKEN_LIFETIME
        token = jwt.encode({'user_id': user_id, 'role': role, "name": name, 'user_name': user_name, 'exp': token_exp}, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_token(self, token):
        payload, _ = self.decode_token(token)
        return payload is not None

    def decode_token(self, token):
        """Decode a token.

        Always returns a (payload, error) tuple: (dict, None) on success,
        (None, message) on failure.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return None, 'Token has expired'
        except jwt.InvalidSignatureError:
            return None, 'Token has invalid signature'
        except jwt.InvalidTokenError:
            return None, 'Error decoding token'
        if not isinstance(payload, dict):
            return None, 'Error decoding token'
        return payload, None
