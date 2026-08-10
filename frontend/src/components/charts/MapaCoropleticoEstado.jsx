# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import json

import plotly.express as px
import plotly.graph_objects as go

from pysus.online_data.SIH import download as download_sih
from pysus.online_data.CNES import download as download_cnes


# ==========================================================
# GEOJSON
# ==========================================================
GEOJSON_PATHS = {
    'AC': 'geojs-12-mun','AL': 'geojs-27-mun','AP': 'geojs-16-mun',
    'AM': 'geojs-13-mun','BA': 'geojs-29-mun','CE': 'geojs-23-mun',
    'DF': 'geojs-53-mun','ES': 'geojs-32-mun','GO': 'geojs-52-mun',
    'MA': 'geojs-21-mun','MT': 'geojs-51-mun','MS': 'geojs-50-mun',
    'MG': 'geojs-31-mun','PA': 'geojs-15-mun','PB': 'geojs-25-mun',
    'PR': 'geojs-41-mun','PE': 'geojs-26-mun','PI': 'geojs-22-mun',
    'RJ': 'geojs-33-mun','RN': 'geojs-24-mun','RS': 'geojs-43-mun',
    'RO': 'geojs-11-mun','RR': 'geojs-14-mun','SC': 'geojs-42-mun',
    'SP': 'geojs-35-mun','SE': 'geojs-28-mun','TO': 'geojs-17-mun',
    'BR': 'geojs-100-mun'
}


# ==========================================================
# BASE POPULAÇÃO
# ==========================================================
def carregar_base(path_csv, ano):

df = pd.read_csv(path_csv, sep=';', dtype=str)

df['ano'] = df['ano'].astype(int)
df['populacao'] = pd.to_numeric(df['populacao'], errors='coerce')

df = df[df['ano'] == ano]

return df[['cod_mun_ibge_6','municipio','UF','populacao']].drop_duplicates()


# ==========================================================
# SIH (FLUXO)
# ==========================================================
def carregar_fluxo_sih(ufs, anos, cid_prefix=None):

dfs = []

for uf in ufs:
    for ano in anos:
        try:
        files = download_sih(
            states=uf,
            years=ano,
            months=list(range(1,13)),
                             groups="RD"
        )

        if isinstance(files, list):
            dfs.extend([f.to_dataframe() for f in files])
            else:
                dfs.append(files.to_dataframe())

                except Exception as e:
                print(f"⚠️ SIH erro {uf}/{ano}: {e}")

                if not dfs:
                    return pd.DataFrame()

                    df = pd.concat(dfs, ignore_index=True)

                    df['MUNIC_RES'] = df['MUNIC_RES'].astype(str).str[:6]
                    df['MUNIC_MOV'] = df['MUNIC_MOV'].astype(str).str[:6]

                    df['MES'] = df['MES_CMPT']

                    if cid_prefix:
                        df = df[df['DIAG_PRINC'].astype(str).str.startswith(tuple(cid_prefix))]

                        df = df[df['MUNIC_RES'] != df['MUNIC_MOV']]

                        df = df.groupby(['MUNIC_RES','MUNIC_MOV','MES']).size().reset_index(name='N_PACIENTES')

                        return df


                        # ==========================================================
                        # CNES (CAPACIDADE)
                        # ==========================================================
                        def carregar_cnes(ufs, anos):

                        dfs = []

                        for uf in ufs:
                            for ano in anos:
                                try:
                                files = download_cnes(
                                    states=uf,
                                    years=ano,
                                    months=[12],
                                    group="LT"
                                )

                                if isinstance(files, list):
                                    dfs.extend([f.to_dataframe() for f in files])
                                    else:
                                        dfs.append(files.to_dataframe())

                                        except Exception as e:
                                        print(f"⚠️ CNES erro {uf}/{ano}: {e}")

                                        if not dfs:
                                            return pd.DataFrame(columns=["cod_mun_ibge_6","CAPACIDADE"])

                                            df = pd.concat(dfs, ignore_index=True)

                                            df['CODUFMUN'] = df['CODUFMUN'].astype(str).str[:6]
                                            df['QT_EXIST'] = pd.to_numeric(df['QT_EXIST'], errors='coerce').fillna(0)

                                            return df.groupby('CODUFMUN')['QT_EXIST'].sum().reset_index().rename(
                                                columns={'CODUFMUN':'cod_mun_ibge_6','QT_EXIST':'CAPACIDADE'}
                                            )


                                            # ==========================================================
                                            # RISCO
                                            # ==========================================================
                                            def calcular_risco(df_fluxo, base, capacidade):

                                            carga = df_fluxo.groupby('MUNIC_MOV')['N_PACIENTES'].sum().reset_index()
                                            carga.rename(columns={'MUNIC_MOV':'cod_mun_ibge_6','N_PACIENTES':'CARGA'}, inplace=True)

                                            df = base.copy()

                                            df = df.merge(carga, on='cod_mun_ibge_6', how='left')
                                            df = df.merge(capacidade, on='cod_mun_ibge_6', how='left')

                                            df['CARGA'] = df['CARGA'].fillna(0)
                                            df['CAPACIDADE'] = df['CAPACIDADE'].fillna(0)
                                            df['populacao'] = df['populacao'].fillna(0)

                                            df['PER_CAPITA'] = df['CARGA'] / (df['populacao'] + 1)
                                            df['SOBRECARGA'] = df['CARGA'] / (df['CAPACIDADE'] + 1)

                                            def norm(x):
                                            return (x-x.min())/(x.max()-x.min()) if x.max()!=x.min() else x*0

                                            df['SCORE'] = 0.5*norm(df['PER_CAPITA']) + 0.5*norm(df['SOBRECARGA'])
                                            df['RANK'] = df['SCORE'].rank(ascending=False)

                                            return df


                                            # ==========================================================
                                            # MAPA (LÓGICA DO REACT)
                                            # ==========================================================
                                            def mapa_plotly(df, ufs, output_dir):

                                            RAIZ = Path(__file__).resolve().parent.parent.parent
                                            GEO_DIR = RAIZ / "src/geojson_uf"

                                            key = 'BR' if len(ufs) > 1 else ufs[0]
                                            geo_file = GEO_DIR / f"{GEOJSON_PATHS[key]}.json"

                                            geojson = json.load(open(geo_file, encoding='utf-8'))

                                            df['cod_mun_ibge_7'] = df['cod_mun_ibge_6'].astype(str).str.zfill(6) + "0"

                                            data_map = {
                                                str(row.cod_mun_ibge_7): row
                                                for row in df.itertuples()
                                            }

                                            locations = []
                                            z_values = []
                                            hover = []

                                            for feature in geojson['features']:

                                                geo_id = str(feature['properties']['id'])
                                                nome = feature['properties'].get('nome', 'Município')

                                                locations.append(geo_id)

                                                if geo_id in data_map:

                                                    row = data_map[geo_id]

                                                    z_values.append(row.SCORE)

                                                    hover.append(
                                                        f"{row.municipio} ({row.UF})<br>"
                                                        f"Carga: {row.CARGA:.0f}<br>"
                                                        f"Capacidade: {row.CAPACIDADE:.0f}<br>"
                                                        f"Score: {row.SCORE:.3f}"
                                                    )

                                                    else:
                                                        z_values.append(None)
                                                        hover.append(f"{nome}<br>Sem dados")

                                                        fig = go.Figure(go.Choropleth(
                                                            geojson=geojson,
                                                            locations=locations,
                                                            z=z_values,
                                                            text=hover,
                                                            hoverinfo="text",
                                                            featureidkey="properties.id",
                                                            colorscale="Reds",
                                                            marker_line_color="white",
                                                            marker_line_width=0.5
                                                        ))

                                                        fig.update_geos(fitbounds="locations", visible=False)

                                                        out = Path(output_dir) / f"mapa_{key}.html"
                                                        fig.write_html(out)

                                                        print(f"🗺️ Mapa salvo em: {out}")


                                                        # ==========================================================
                                                        # FLUXO ANIMADO
                                                        # ==========================================================
                                                        def fluxo_animado(df_fluxo, output_dir):

                                                        RAIZ = Path(__file__).resolve().parent.parent.parent
                                                        geo = json.load(open(RAIZ / "src/geojson_uf/geojs-100-mun.json"))

                                                        coords = {}

                                                        for f in geo['features']:
                                                            cod = str(f['properties']['id'])[:6]
                                                            poly = f['geometry']['coordinates'][0]

                                                            lon = np.mean([p[0] for p in poly])
                                                            lat = np.mean([p[1] for p in poly])

                                                            coords[cod] = (lat, lon)

                                                            df = df_fluxo.copy()

                                                            df['orig_lat'] = df['MUNIC_RES'].map(lambda x: coords.get(x,(None,None))[0])
                                                            df['orig_lon'] = df['MUNIC_RES'].map(lambda x: coords.get(x,(None,None))[1])
                                                            df['dest_lat'] = df['MUNIC_MOV'].map(lambda x: coords.get(x,(None,None))[0])
                                                            df['dest_lon'] = df['MUNIC_MOV'].map(lambda x: coords.get(x,(None,None))[1])

                                                            df = df.dropna()

                                                            frames = []

                                                            for mes in sorted(df['MES'].unique()):

                                                                subset = df[df['MES'] == mes]

                                                                data = [
                                                                    go.Scattergeo(
                                                                        lon=[r.orig_lon, r.dest_lon],
                                                                        lat=[r.orig_lat, r.dest_lat],
                                                                        mode='lines',
                                                                        line=dict(width=max(r.N_PACIENTES/50, 1)),
                                                                                  opacity=0.4
                                                                    )
                                                                    for r in subset.itertuples()
                                                                ]

                                                                frames.append(go.Frame(data=data, name=str(mes)))

                                                                fig = go.Figure(data=frames[0].data, frames=frames)

                                                                fig.update_layout(
                                                                    title="Fluxo Mensal de Pacientes",
                                                                    geo=dict(scope='south america'),
                                                                                  updatemenus=[{
                                                                                      "type": "buttons",
                                                                                      "buttons": [{"label": "Play", "method": "animate", "args": [None]}]
                                                                                  }]
                                                                )

                                                                out = Path(output_dir) / "fluxo_animado.html"
                                                                fig.write_html(out)

                                                                print(f"🎬 Fluxo salvo em: {out}")


                                                                # ==========================================================
                                                                # MAIN
                                                                # ==========================================================
                                                                def main(args):

                                                                base = carregar_base(args.pop_csv, args.anos[0])
                                                                df_fluxo = carregar_fluxo_sih(args.ufs, args.anos, args.cid)

                                                                if df_fluxo.empty:
                                                                    print("❌ Sem dados")
                                                                    return

                                                                    capacidade = carregar_cnes(args.ufs, args.anos)
                                                                    df_risco = calcular_risco(df_fluxo, base, capacidade)

                                                                    Path(args.output).mkdir(parents=True, exist_ok=True)

                                                                    df_risco.to_csv(Path(args.output)/"risco.csv", sep=';', index=False)

                                                                    print("\n🏆 TOP 10:")
                                                                    print(df_risco.sort_values("SCORE", ascending=False)[
                                                                        ['municipio','UF','SCORE']
                                                                    ].head(10))

                                                                    if args.mapa:
                                                                        mapa_plotly(df_risco, args.ufs, args.output)

                                                                        if args.fluxo:
                                                                            fluxo_animado(df_fluxo, args.output)


                                                                            # ==========================================================
                                                                            # CLI
                                                                            # ==========================================================
                                                                            if __name__ == "__main__":

                                                                                parser = argparse.ArgumentParser()

                                                                                parser.add_argument("--ufs", nargs="+", default=["TO"])
                                                                                parser.add_argument("--anos", nargs="+", type=int, default=[2022])

                                                                                parser.add_argument("--cid", nargs="+")
                                                                                parser.add_argument("--mapa", action="store_true")
                                                                                parser.add_argument("--fluxo", action="store_true")

                                                                                parser.add_argument("--output", default="outputs")
                                                                                parser.add_argument("--pop_csv", default="populacao_estimada_completa_spline.csv")

                                                                                args = parser.parse_args()
                                                                                main(args)
