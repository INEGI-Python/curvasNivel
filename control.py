
import json,os
from dotenv import load_dotenv
load_dotenv()

class Seguimiento:
    def __init__(self,t):
        self.tipo = t
        self.divisor = 0
        self.inicio = False

    def inicia(self,t=0):
        obj = dict(total=t,procesados=0,porcentaje=0.0)
        self.divisor=int(t/25)
        os.environ[self.tipo] = json.dumps(obj)
        self.inicio=True

    def actualizar(self,inc=1):
        if self.inicio: 
            obj=json.loads(os.getenv(self.tipo))
            obj["procesados"]+=inc
            obj["porcentaje"]= round((obj["procesados"]/obj["total"])*100,2)
            if obj["procesados"] % self.divisor == 0:
                #os.system("cls" if os.name == "nt" else "clear")
                print(f"." * (obj["procesados"]//self.divisor) + " " * ((obj["total"] - obj["procesados"])//self.divisor), end=f"{obj["porcentaje"]}%\n")
            os.environ[self.tipo] = json.dumps(obj)
        else:
            print(f"[ ¡¡ ] No se ha iniciado el seguimiento para este procedimiento. Use la clase Seguimiento(tipo,divisor).inicia(totalElementos) ")

