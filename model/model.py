class User:
    def __init__(self, _id, user_name, password, phone_number,basari_puani,user_type,kayit_tarihi):
        self._id = _id
        self.user_name = user_name
        self.password = password
        self.phone_number = phone_number
        self.basari_puani = basari_puani
        self.tamamlanan_gun = 0
        self.user_type = user_type
        self.kayit_tarihi = kayit_tarihi
        
        
    def get_id(self):
        return self._id

    def set_id(self, new_id):
        self._id = new_id

    def get_user_name(self):
        return self.user_name

    def set_user_name(self, new_user_name):
        self.user_name = new_user_name

    def get_password(self):
        return self.password

    def set_password(self, new_password):
        self.password = new_password

    def get_phone_number(self):
        return self.phone_number

    def set_phone_number(self, phone_number):
        self.phone_number = phone_number

    def get_user_type(self):
        return self.phone_number

    def set_user_type(self, new_phone_number):
        self.phone_number = new_phone_number

    def get_kayit_tarihi(self):
        return self.kayit_tarihi
    
    def get_tamamlanan_gun(self):
        return self.tamamlanan_gun
    
    def set_tamamlanan_gun(self,i):
        return self.tamamlanan_gun + 1 
    

class Egzersiz:
    def __init__(self, _id, name, text, egzersiz_puanı, egzersiz_seviyesi):
        self._id = _id
        self.name = name
        self.text = text
        self.egzersiz_puanı = egzersiz_puanı
        self.egzersiz_seviyesi = egzersiz_seviyesi

    # Getter ve Setter metotları
    def get_id(self):
        return self._id
    
    def set_id(self, _id):
        self._id = _id
    
    def get_name(self):
        return self.name
    
    def set_name(self, name):
        self.name = name
    
    def get_text(self):
        return self.text
    
    def set_text(self, text):
        self.text = text
    
    def get_egzersiz_puani(self):
        return self.egzersiz_puani
    
    def set_egzersiz_puani(self, egzersiz_puani):
        self.egzersiz_puani = egzersiz_puani
    
    def get_egzersiz_seviyesi(self):
        return self.egzersiz_seviyesi
    
    def set_egzersiz_seviyesi(self, egzersiz_seviyesi):
        self.egzersiz_seviyesi = egzersiz_seviyesi
      
        
class Story:
    def __init__(self,_id,text,seviye) :
        self._id = _id
        self.text =text
        self.seviye = seviye
    
    def get_metin_seviyesi(self):
        return self.egzersiz_seviyesi
    
    def set_metin_seviyesi(self, egzersiz_seviyesi):
        self.egzersiz_seviyesi = egzersiz_seviyesi
      
    def get_text(self):
        return self.text
    
    def set_text(self, text):
        self.text = text
    