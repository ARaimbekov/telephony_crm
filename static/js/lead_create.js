function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

let atc_field = document.getElementById("div_id_atc")
let number_field = document.querySelector("div.relative select[name='phone_number']")
atc_field.addEventListener("change", getAtcId)


function getAtcId(e) {
    let atc_id = e.target.value


    const data = { id: atc_id };

    let url = " {% url 'leads:lead-phone' %} "

    fetch(url, {
        method: 'POST', // or 'PUT'
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify(data),
    })
        .then((response) => response.json())

        .then((data) => {
            console.log('Success:', data);

            if (data.length != 0) {
                number_field.innerHTML = `<option value="${data[0]["id"]}" id="number-id-field">${data[0]["name"]}</option>`


                for (let i = 1; i < data.length; i++) {
                    number_field.innerHTML += `<option value="${data[i]["id"]}" id="number-id-field">${data[i]["name"]}</option>`
                }

            } else {
                number_field.innerHTML = '<option value="" id="number-id-field">Нет свободных номеров</option>'

            }


        })
        .catch((error) => {
            console.error('Error:', error);
        });

}