
import json,os,sys
from dotenv import load_dotenv
load_dotenv()

class Seguimiento:
    def __init__(self,t):
        self.tipo = t
        self.divisor = 0
        self.x = 1
        self.y = 1

    def inicia(self,t=0):
        tmp = open("temp","w") 
        obj = dict(iniciado=True,total=t,procesados=0,porcentaje=0)
        self.divisor=int(t/100)
        os.environ[self.tipo] = json.dumps(obj)
        tmp.write(json.dumps(obj))
        tmp.close()

    def actualizar(self,inc=1):
        tmp = open("temp", "r+")
        obj = json.loads(tmp.read())
        if obj["iniciado"]:
            obj["procesados"]+=inc
            obj["porcentaje"]= round((obj["procesados"]/obj["total"])*100,2)
            if obj["procesados"] % self.divisor == 0:
                #os.system("cls" if os.name == "nt" else "clear")
                text = f"{self.fecha()}  " + "." * (obj["procesados"]//self.divisor) + " " * ((obj["total"] - obj["procesados"])//self.divisor) + f"{obj["porcentaje"]}%\n"
                sys.stdout.write(f"\033[{self.y};{self.x}H{text}")
                sys.stdout.flush()
            tmp.seek(0)
            tmp.write(json.dumps(obj))
            tmp.truncate()
            os.environ[self.tipo] = json.dumps(obj)
            tmp.close()
        else:
            print(f"[ ¡¡ ] No se ha iniciado el seguimiento para este procedimiento. Use la clase Seguimiento(tipo,divisor).inicia(totalElementos) para iniciar el seguimiento.")

    def fecha(self):
        import datetime as dt   
        mes = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        t = dt.datetime.today()
        d = str(t)[5:-5]
        return f"|{d[3:5]} de {mes[int(d[0:2])-1] } {d[6:]}|"
        
    
    def imp(self,text):
        text = f"{self.fecha()}  {str(text)}"
        open("registro.log", "a").write(text+"\n")
        print(text)
        #sys.stdout.write(f"\033[{self.y};{self.x}H{text}")
        #sys.stdout.flush()
        self.y += 1
