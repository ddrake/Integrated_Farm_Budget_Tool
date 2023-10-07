function makeRequest(state_id) {
  xhr = new XMLHttpRequest();

  if (!xhr) {
    alert("Giving up :( Cannot create an XMLHTTP instance");
    return false;
  }
  xhr.onreadystatechange = updateCounties;
  const url = `counties_for_state/${state_id}`
  xhr.open("GET", url);
  xhr.send();
}

function updateCounties() {
  if (xhr.readyState === XMLHttpRequest.DONE) {
    if (xhr.status === 200) {
        let options = '';
        const resp = JSON.parse(xhr.responseText);
        resp.data.forEach(cty => {
            options += `<option value=${cty[0]}>${cty[1]}</option>\n`;
        });
        document.getElementById("county_code").innerHTML = options;
    } else {
      alert("Request for counties failed.");
    }
  }
}
