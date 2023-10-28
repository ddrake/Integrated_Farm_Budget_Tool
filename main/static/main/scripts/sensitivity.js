function createButtonBar(nincr, basis_incr, farmyear) {
  if (basis_incr === 0)
    return;

  const btnBarContainer = document.createElement("div")
  const btnBarLabel = document.createElement("div")
  const btnBar = document.createElement("div");
  btnBarContainer.setAttribute('id', 'btnBarContainer')
  btnBarContainer.setAttribute('class', 'flex flex-col bg-white')
  btnBarLabel.setAttribute('id', 'btnBarLabel')
  btnBarLabel.setAttribute('class', 'text-left text-sm px-1 pb-1 text-gray-700 font-bold')
  const btnBarLabelContent = document.createTextNode('Increment to Assumed Basis')
  btnBarLabel.appendChild(btnBarLabelContent)
  btnBar.setAttribute('id', 'btnBar')
  btnBar.setAttribute('class', ('w-fit flex flex-row text-sm border border-gray-300 ' +
                      'rounded-lg p-1'))
  const nst = (nincr - 1)/2
  const basisIncrArray = Array.from({ length: nincr }, (_, i) => -nst + i)
                              .map((x) => (x*basis_incr).toFixed(2).split("-"))
                              .map((x) => x.length === 1 ? '$'+x[0] : '-$'+x[1]);
  basisIncrArray.forEach(function(value, i) {
    const btn = document.createElement("div")
    btn.setAttribute('id', `btn${i}`)
    btn.setAttribute('class',('btn flex box-border border-2 border-slate-300 w-16 ' +
      'h-8 items-center justify-center bg-indigo-100 hover:bg-indigo-50 cursor-pointer'))
    const btnContent = document.createTextNode(value)
    btn.appendChild(btnContent)
    btn.addEventListener('click', (event) => {
      setSelectedButton(event.target)
      makeRequest(farmyear, basis_incr) 
    })
    btnBar.appendChild(btn)
  })
  btnBarContainer.appendChild(btnBarLabel)
  btnBarContainer.appendChild(btnBar)

  // add the newly created element and its content into the DOM
  const cropSel = document.getElementById("crop-sel");
  cropSel.after(btnBarContainer);
  // select the center button ($0.00) by default
  let btn = document.getElementById(`btn${(nincr-1)/2}`)
  setSelectedButton(btn)
}

function setSelectedButton(elSel) {
  document.querySelectorAll('#btnBar .selected').forEach((el) => {
    el.classList.remove('selected', 'border-indigo-700', 'bg-indigo-200',
                        'cursor-default')
    el.classList.add('border-slate-300', 'bg-indigo-100', 'hover:bg-indigo-50',
                     'cursor-pointer')
  })
  elSel.classList.remove('border-slate-300', 'bg-indigo-100',
                         'hover:bg-indigo-50', 'cursor-pointer')
  elSel.classList.add('selected', 'border-indigo-700',
                      'bg-indigo-200', 'cursor-default')
}

function manageButtonbarVisibility(basis_incr) {
  if (basis_incr === 0)
    return;
  let buttonBar = document.querySelector("#btnBarContainer")
  let type = document.querySelector("#type-sel").value
  buttonBar.style.display = 
    ['revenue', 'cashflow'].includes(type) ? 'flex' : 'none'
}

function getTblInfo(basis_incr) {
  diffcb = document.querySelector("#diff")
  let diff = (diffcb ? document.querySelector("#diff").checked : false)
  let type = document.querySelector("#type-sel").value
  let crop = document.querySelector("#crop-sel").value
  let basistype = ['revenue', 'cashflow'].includes(type)
  let tblnum = ''
  if (basis_incr !== 0 && basistype) {
    let btnSel = document.querySelectorAll('#btnBar .selected')
    tblnum = btnSel[0].id[3]
  }
  return {'tbltype': type, 'crop': crop, 'tblnum': tblnum, 'isdiff': diff}
}

function makeRequest(farmyear, basis_incr) {
  ti = getTblInfo(basis_incr)
  xhr = new XMLHttpRequest();

  if (!xhr) {
    alert("Giving up :( Cannot create an XMLHTTP instance");
    return false;
  }
  xhr.onreadystatechange = replaceTable;
  const url = `sens_table/` +
    `?tbltype=${ti.tbltype}&crop=${ti.crop}&tblnum=${ti.tblnum}&isdiff=${ti.isdiff}`

  xhr.open("GET", url);
  xhr.send();
}

function replaceTable() {
  if (xhr.readyState === XMLHttpRequest.DONE) {
    if (xhr.status === 200) {
        const resp = JSON.parse(xhr.responseText);
        newtbody = makeTbody(resp.data)
        oldtbody = document.querySelector("#senstable tbody")
        parent = document.querySelector("#senstable")
        parent.replaceChild(newtbody, oldtbody)
    } else {
      alert("Failed to replace sensitivity table.");
    }
  }
}

function makeTbody(table) {
  const tbody = document.createElement("tbody")
  table.forEach(row => {
    let tr = document.createElement("tr")
    row.forEach(col => {
      let td = document.createElement("td")
      if (col[1]) {
        td.setAttribute('colspan', `${col[1]}`)
      }
      td.setAttribute('class', `px-1 py-0 ${col[2]}`)
      let txt = document.createTextNode(`${col[0]}`)
      td.appendChild(txt)
      tr.appendChild(td)
    })
    tbody.appendChild(tr)
  });
  return tbody
}
