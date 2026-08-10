function getCookie(name) {
    // pega o cookie do navegador
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

const res = await axios.post('http://127.0.0.1:8000/api/pipelines/indicadores/trigger/', formData, {
    headers: {
        'Authorization': `Token ${token}`,
        'X-CSRFToken': csrftoken,
    },
    withCredentials: true,
});
