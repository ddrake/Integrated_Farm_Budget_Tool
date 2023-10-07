    function createButtonBar(nincr, basis_incr) {
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
      managevisibility()
    }

    function manageButtonbarVisibility(basis_incr) {
      if (basis_incr === 0)
        return;
      let buttonBar = document.querySelector("#btnBarContainer")
      let type = document.querySelector("#type-sel").value
      buttonBar.style.display = 
        ['revenue', 'cashflow'].includes(type) ? 'flex' : 'none'
    }

    function managevisibility(basis_incr) {
      tblid = getTblId(basis_incr)
      const matches = document.querySelectorAll(".stbl");
      matches.forEach((tbl) => {
        if (tbl.id !== tblid) {
          tbl.style.display = 'none';
        }
        else {
          tbl.style.display = 'block';
        }
      })
    }

    function getTblId(basis_incr) {
      let tblid = ''
      diffcb = document.querySelector("#diff")
      let diff = (diffcb ? document.querySelector("#diff").checked : false)
      let type = document.querySelector("#type-sel").value
      let crop = document.querySelector("#crop-sel").value
      let basistype = ['revenue', 'cashflow'].includes(type)
      if (basis_incr === 0 || !basistype) {
        tblid = type + (diff ? '_diff' : '') + `_${crop}`
      }
      else {
        let btnSel = document.querySelectorAll('#btnBar .selected')
        console.log(btnSel)
        let table_num = btnSel[0].id[3]
        console.log(table_num, 'again')
        tblid = `${type}` + (diff ? '_diff' : '') + `_${table_num}_${crop}`
      }
      return tblid
    }
