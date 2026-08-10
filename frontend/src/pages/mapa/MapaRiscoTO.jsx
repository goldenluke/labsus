import React, { useEffect, useState } from "react";
import Plot from "react-plotly.js";

export default function MapaRiscoTO() {
  const [dados, setDados] = useState([]);
  const [minuta, setMinuta] = useState("");
  const [municipioSelecionado, setMunicipioSelecionado] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/risco-minuta/")
      .then(res => res.json())
      .then(data => setDados(data.data || []));
  }, []);

  const handleClick = async (e) => {
    const point = e.points?.[0];
    if (!point) return;

    const codigo = point.location;
    const municipio = dados.find(d => String(d.codigo) === String(codigo));

    if (!municipio) return;

    setMunicipioSelecionado(municipio);

    const res = await fetch(
      `http://localhost:8000/api/minuta-auto/?municipio=${municipio.municipio}&risco=${municipio.risco}`
    );

    const json = await res.json();
    setMinuta(json.texto);
  };

  return (
    <div style={{ display: "flex", height: "100vh", background: "#0f172a" }}>
      
      {/* MAPA */}
      <div style={{ width: "65%" }}>
        <Plot
          data={[
            {
              type: "choropleth",
              geojson: "/geojs-17-mun.json",
              locations: dados.map(d => String(d.codigo)),
              z: dados.map(d => d.risco),
              text: dados.map(d => d.municipio),
              hoverinfo: "text",
              featureidkey: "properties.id",
              colorscale: [
                [0, "#22c55e"],
                [0.5, "#facc15"],
                [1, "#ef4444"]
              ]
            }
          ]}
          layout={{
            geo: { fitbounds: "locations", visible: false },
            paper_bgcolor: "#0f172a"
          }}
          onClick={handleClick}
          style={{ width: "100%", height: "100%" }}
        />
      </div>

      {/* PAINEL */}
      <div style={{
        width: "35%",
        padding: 20,
        color: "white",
        overflow: "auto",
        background: "#020617"
      }}>
        {!municipioSelecionado && <p>Clique em um município</p>}

        {municipioSelecionado && (
          <>
            <h2>{municipioSelecionado.municipio}</h2>
            <p>Risco: {municipioSelecionado.risco}</p>

            <hr />

            <pre style={{ whiteSpace: "pre-wrap" }}>
              {minuta}
            </pre>
          </>
        )}
      </div>

    </div>
  );
}
