// src/api/pipeline.js
import { getCookie } from "../utils/cookies";

export async function triggerPipeline(params = {}) {
    const csrftoken = getCookie("csrftoken");

    const response = await fetch("http://localhost:8000/api/pipelines/indicadores/trigger/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken, // importante
        },
        credentials: "include", // necessário para enviar cookies
        body: JSON.stringify(params),
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Erro: ${response.status} - ${error}`);
    }

    return response.json();
}
