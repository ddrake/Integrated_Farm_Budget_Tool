function makeRequest(budgettype, farmyear) {
  xhr = new XMLHttpRequest();

  if (!xhr) {
    alert("Giving up :( Cannot create an XMLHTTP instance");
    return false;
  }
  xhr.onreadystatechange = updateBudget;
  const url = `table/?bdgtype=${budgettype}`

  xhr.open("GET", url);
  xhr.send();
}

function updateBudget() {
  if (xhr.readyState === XMLHttpRequest.DONE) {
    if (xhr.status === 200) {
        const resp = JSON.parse(xhr.responseText);
        updateTables(resp.data)
    } else {
      alert("Failed to replace sensitivity table.");
    }
  }
}

function updateTables(data) {
  updateRowsWithRowHead(data.rev, "#revcalctable tbody tr")
  updateBudgetTables(data.tables)
}

function updateBudgetTables(tables) {
    updateRowsWithRowHead(tables.kd, "#kdtable tbody tr")
    updateRowsWithoutRowHead(tables.pa, "#patable tbody tr")
    updateRowsWithoutRowHead(tables.pb, "#pbtable tbody tr")
    if (tables.wheatdc) {
         updateRowsWithoutRowHead(tables.wheatdc, "#wheatdctable tbody tr")
    }
}

function updateRowsWithRowHead(rows, selstr) {
    let tr = document.querySelector(selstr)
    // skip col header rows
    rows[0].forEach((it) => {
        tr = tr.nextElementSibling;
    })
    rows[1].forEach((it) => {
        let td = tr.firstElementChild;
        // skip row header
        td = td.nextElementSibling;
        it[1].forEach((val) => {
            td.innerHTML = val
            if (td.classList.contains("addspace")) {
                td.innerHTML = '&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;'
            }
            td = td.nextElementSibling;
        })
        tr = tr.nextElementSibling;
    })
}

function updateRowsWithoutRowHead(rows, selstr) {
    let tr = document.querySelector(selstr)
    // skip col header rows
    rows[0].forEach((it) => {
        tr = tr.nextElementSibling;
    })
    rows[1].forEach((it) => {
        let td = tr.firstElementChild;
        it.forEach((val) => {
            td.innerHTML = val
            td = td.nextElementSibling;
        })
        tr = tr.nextElementSibling;
    })
}
