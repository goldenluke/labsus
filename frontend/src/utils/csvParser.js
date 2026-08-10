// src/utils/csvParser.js
export const parseCSV = (data) => {
    // Assuming 'data' is already an array of objects from Django's JSON response
    // Django's ManagedFileDataAPIView already returns data as parsed JSON,
    // so this function might just return the data directly if it's not a raw CSV string.
    // If your Django API were returning a raw CSV string, this function would parse it.
    // Based on your current setup, the Django API already gives parsed JSON.

    // This is a placeholder. If your Django API is correctly returning a JSON array of objects,
    // this function just needs to normalize it if necessary.
    // For example, ensuring numbers are numbers and not strings from CSV columns not covered by dtype.

    // Your previous logic for converting numbers from string (if needed) was:
    // const metadataColumns = ['cod_mun_ibge_6', 'municipio', 'UF', 'cod_mun_ibge_7', 'perfil', 'nome_uf', 'ANO', 'populacao'];
    // const numericKeys = Object.keys(data[0] || {}).filter(key => !metadataColumns.includes(key));
    // No entanto, como o backend agora lida com ANO e populacao via dtype,
    // e outros indicadores via `parseFloat` no frontend, a necessidade de `parseCSV` é reduzida
    // a apenas garantir que o `data` seja um array de objetos.

    if (!Array.isArray(data)) {
        console.error("parseCSV: Expected an array of objects, received:", data);
        return [];
    }

    // Apply a general numeric conversion if your backend doesn't handle ALL numeric types
    // This part might be redundant if your backend (api/views.py) already handles all numeric conversions to float.
    // It's safer to rely on the backend's `dtype_mapping` for accuracy.
    // However, if some numeric fields *still* arrive as strings, this re-parses them.
    return data.map(item => {
        const newItem = { ...item };
        for (const key in newItem) {
            if (typeof newItem[key] === 'string' && !isNaN(parseFloat(newItem[key].replace(',', '.')))) {
                newItem[key] = parseFloat(newItem[key].replace(',', '.'));
            }
        }
        return newItem;
    });
};
