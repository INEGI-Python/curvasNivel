import sys
from time import time as t
import os
import geopandas as geo
import matplotlib.pyplot as plt
from multiprocessing import Pool,cpu_count
from pyproj import CRS
import argparse,json
from shapely.geometry import LineString,Polygon,MultiPolygon,Point
from control import Seguimiento
from dotenv import load_dotenv
load_dotenv()



class AnalisisTopografico:
    def __init__(self,dat):
        self.gpkg= dat["gpkg"]  
        self.capas = dat["capas"]   
        self.CRS=CRS.from_epsg(6372)
        self.control=None
        self.corrientesLinea = geo.read_file(self.gpkg, layer=self.capas[1],mask=self.getPolEdo(dat["e"]))
        self.corrientesLinea.to_crs(crs=self.CRS,inplace=True)
        self.corrientesLinea["indice"]=self.corrientesLinea.index
        self.corrientesLinea.set_index("indice",inplace=True)
        self.corrientesLinea["interCurvas"]=None


        self.corrientesArea = geo.read_file(self.gpkg, layer=self.capas[2],mask=self.getPolEdo(dat["e"]))
        self.corrientesArea.to_crs(crs=self.CRS,inplace=True)
        self.corrientesArea["interCurvas"]=None
        self.corrientesArea.set_index("id",inplace=True)


        self.cuerposAgua = geo.read_file(self.gpkg, layer=self.capas[3],mask=self.getPolEdo(dat["e"]))
        self.cuerposAgua.to_crs(crs=self.CRS,inplace=True)
        self.cuerposAgua.set_index("id",inplace=True)
        self.cuerposAgua["interCurvas"]=None

    def getPolEdo(s,edo):
        def multipolygon_to_polygon(geom):
            if geom is None:
                return geom
            if isinstance(geom, Polygon):
                return geom
            if isinstance(geom, MultiPolygon):
                return max(geom, key=lambda g: g.area)
            return geom
        
        if edo is None: return None
        edos = geo.read_file("datos/pol_edos.geojson")
        edos.to_crs(crs="EPSG:6372",inplace=True)
        return  multipolygon_to_polygon(edos.iloc[edos["CVEGEO"]==edo].geometry).buffer(0) 


    def validaLogicaCorrienteAgua(self):
        ids=[]
        for i,row in self.corrientesLinea.iterrows():
            obj = row["interCurvas"]
            mini = 0
            for o in obj:
                if mini>o["z"]:
                    ids.append(i)
                    break
                else:
                    mini=o["z"]
        return ids




    def cortaLinea(self):
        segmentos = []
        for geom in self.corrientesLinea.geometry:
            if geom is None:
                continue
            if geom.geom_type == 'LineString':
                coords = list(geom.coords)
                for i in range(len(coords)-1):
                    segmentos.append(LineString([coords[i], coords[i+1]]))
            elif geom.geom_type == 'MultiLineString':
                for part in geom.geoms:
                    coords = list(part.coords)
                    for i in range(len(coords)-1):
                        segmentos.append(LineString([coords[i], coords[i+1]]))
            else:
                segmentos.append(geom)
        return  geo.GeoDataFrame(geometry=segmentos)


    def getCoordCurva(self,linea):
        cosmos = linea.envelope
        curvas = geo.read_file(self.gpkg,layer=self.capas[0],mask=cosmos)
        curvas.to_crs(crs=self.CRS,inplace=True)
        curvas.set_crs(crs=self.CRS,inplace=True,allow_override=True)
        intersecciones =  curvas.iloc[curvas.geometry.intersects(linea)]
        resultados = []
        inicio = Point(linea.coords[0])
        for _, row in intersecciones.iterrows():
            inter = linea.intersection(row.geometry)
            dist = inicio.distance(row.geometry)
            if inter.is_empty:
                continue
            if inter.geom_type == "Point":
                resultados.append(dict(x=inter.x,y=inter.y,z=row["elevacion"],d=dist))
            if inter.geom_type in ("MultiPoint", "GeometryCollection"):
                for geom in inter.geoms:
                    if geom.geom_type == "Point":
                        resultados.append(dict(x=geom.x,y=geom.y,z=row["elevacion"],d=dist))
        resultados.sort(key=lambda item: item["d"])
        self.control.actualizar(1) 
        del cosmos,curvas,intersecciones,inicio
        return resultados

    def lineaCentral(self):
        rioPol = geo.GeoDataFrame(geometry=self.corrientesArea.segmentize(20).geometry)
        rioPol.to_crs(crs=self.CRS,inplace=True)
        lineas=rioPol.buffer(10).boundary.to_list()
        lineas.extend(rioPol.buffer(-10).boundary)
        rioLin = geo.GeoDataFrame(geometry=lineas)
        rioLin.to_crs(crs=self.CRS,inplace=True)
        voronoi = rioPol.voronoi_polygons().boundary
        clip = voronoi.clip(rioLin)
        voroLin = self.cortaLinea(voronoi)
        central = voroLin.iloc[~voroLin.geometry.intersects(rioLin.union_all())]
        return central            


# def areas2lineas(cca):
#     global CRS
#     _poli = cca.exterior
#     voronoi = _poli.voronoi_polygons()
#     voro_linea = geo.GeoDataFrame(geometry=voronoi.boundary)
#     tmp = cortaLinea(voro_linea.geometry)
#     tmp.set_crs(epsg=CRS,inplace=True)
#     tmp.sindex
#     tmp.is_empty
#     voro_lin2=tmp.clip(cca)
#     contiene=[]
#     for p in cca.buffer(-5).boundary:
#         contiene.extend(voro_lin2.iloc[voro_lin2.geometry.intersects(p)].index)
#     voro_lin2.drop(index=contiene,inplace=True)
#     tmp.build_area()
#     return geo.GeoDataFrame(geometry=voro_lin2.simplify(10))

                            



    def guardaResult(self,gdf,nom,edo):
        if not os.path.exists("Salida"):
            os.makedirs("Salida")
        gdf.to_file(f"Salida/{"Nacional" if edo is None else str(edo)}.gpkg",layer=nom, driver="GPKG")
    



def inicio(_a):
    from conexion_db import engine
    print("[info] Conectando a BD")
    if conn := engine(*list(map(lambda p:os.getenv(p),['HOST','BD','USER','PASS','PORT']))):
        print("[info] Obteniendo las curvas de nivel reproyectadas a EPSG:6372")
        curvasNivel = geo.read_postgis("SELECT id, nom_obj, codigo, calif_pos, tipo, clase_geo, elevacion, ST_Transform(geometria,6372) as geom FROM cnal_topo50_prod.curva_nivel_l_vw",conn)
        curvasNivel.to_file("datos/curvas_nivel_10jun.gpkg",layer="curvasNivel6372",overwrite=True,driver="GPKG")
        del curvasNivel
    analizar = AnalisisTopografico(dict(gpkg="datos/curvas_nivel_10jun.gpkg",capas=["curvasNivel6372","corrientesAguaLinea","corrientesAguaArea","cuerposAgua"],e=_a.e))
    analizar.control = Seguimiento("corrientesLinea")
    imp = analizar.control.imp
    imp(" Iniciando el analisis de las corrientes de agua con las curvas de nivel")
    imp(" ENCONTRANDO LAS CURVAS DE NIVEL QUE LAS CORRIENTES INTERSECTAN EN ORDEN DE EDICION DE LA LINEA DE CORRIENTE DE AGUA")
    tot = len(analizar.corrientesLinea.count_geometries())
    analizar.control.inicia(tot)
    with Pool() as pool:
        res = pool.map(analizar.getCoordCurva,analizar.corrientesLinea.geometry) 
    text = f"{analizar.control.fecha()}  " + "." * (tot//analizar.control.divisor) + "  100% \n"
    sys.stdout.write(f"\033[{analizar.control.y};{analizar.control.x}H{text}")
    sys.stdout.flush()
    analizar.corrientesLinea["interCurvas"] = res
    analizar.guardaResult(analizar.corrientesLinea,"CorrientesInterCurvas",_a.e)
    imp(" Las curvas de nivel que intersecan con cada corriente de agua fueron encontradas satisfactoriamente")
    imp(" Revisando la lógica de la edición de las corrientes de agua... ")
    validar = analizar.validaLogicaCorrienteAgua()
    analizar.guardaResult(analizar.corrientesLinea.iloc[validar],"Corrientes_a_Revisar",_a.e)
    
    ################################################################################
    imp("Obteniendo la línea central de las corrientes tipo área")
    central = analizar.lineaCentral()
    analizar.guardaResult(central,"lineaCentralCorrientesArea",_a.e)

    ##################################################################################
    imp(" Buscando cuerpos de agua que intersectan con alguna curva de nivel")
    for i,row in analizar.cuerposAgua.iterrows():
        if curvasC := geo.read_file(analizar.gpkg,layer=analizar.capas[0],mask=row.geometry):
            analizar.cuerposAgua.loc[i,"curvasInter"]= curvasC.index.to_list()
    analizar.guardaResult(analizar.cuerposAgua,"cuerposAguaIntersec",_a.e)
    return t()
    


        #   corrientes_linea = geo.read_postgis("SELECT id,nom_geo,condicion,fecha_mod,ST_Transform(geometria,6372) as geom FROM  cnal_topo50_prod.ctrl_mov_corriente_ag_l WHERE fecha_mod >'2026-03-30'",conn)   
        #   corrientes_linea.to_file("datos/curvas_nivel_10jun.gpkg",layer="corrientesAguaLinea",overwrite=True,driver="GPKG")
        #   corrientes_area = geo.read_postgis("SELECT id,nom_geo,condicion,fecha_mod,ST_Transform(geometria,6372) as geom FROM  cnal_topo50_prod.ctrl_mov_corriente_ag_a WHERE fecha_mod >'2026-03-30'",conn)   
        #   corrientes_area.to_file("datos/curvas_nivel_10jun.gpkg",layer="corrientesAguaArea",overwrite=True,driver="GPKG")
        #   cuerpos = geo.read_postgis("SELECT id,nom_geo,condicion,fecha_mod,ST_Transform(geometria,6372) as geom FROM  cnal_topo50_prod.ctrl_mov_cuerpo_agua_a,conn)   
        #   cuerpos.to_file("datos/curvas_nivel_10jun.gpkg",layer="cuerposAgua",overwrite=True,driver="GPKG")

        #   del cuerpos, corrientes_area, corrientes_linea



    # edo=geo.GeoDataFrame(geometry=getPolEdo(_a.e))
    # edo.plot()
    # plt.show()
    # capas = [dict(nom="curva_nivel_l_vw",valor=None),dict(nom="corrientesAguaLinea",valor=None),dict(nom="corrientesAguaArea",valor=None),dict(nom="cuerposAgua",valor=None)]
    # for i in range(0,len(capas)):
    #     imp(f" Cargando capa {capas[i]['nom']}")
    #     capas[i]["valor"]=geo.read_file('datos/Aguascalientes.gpkg',layer=f"{capas[i]['nom']}_0{_a.e}")
    #     capas[i]["valor"].set_index("id",inplace=True)
        #capas[i]["valor"].to_crs(crs='EPSG:6372',inplace=True)
        #capas[i]["valor"].set_crs(crs='EPSG:6372',inplace=True,allow_override=True)
        #capas[i]["valor"].to_file("datos/Aguascalientes.gpkg",layer=f"{capas[i]['nom']}_01",overwrite=True,driver="GPKG")

    # for i,d in aguaLinea.iterrows():
    #     tmp = curvas.loc[curvas.geometry.intersects(d.geometry,align=False),"elevacion"].to_list()
    #     aguaLinea.loc[i,"interCurvas"] = tmp
    #     inter.append(dict(linea=i,curvas=tmp))

    # print(aguaLinea)


    #intersecGDF.plot()
    #plt.title("curvas_interseccionadas")
    #plt.show()






if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Inconsistencias de Corrientes de Agua con la curvas de nivel")
    parser.add_argument("--e",type=int, help="Clave geoestadistica de la entidad federativa.", default=None)
    args = parser.parse_args()
    os.system("cls" if os.name == "nt" else "clear")
    t1 = t()
    tiempo = inicio(args)-t1






