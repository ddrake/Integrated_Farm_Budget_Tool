function setinfo(farmcrop_pk, farmyear_pk) {
  // manage info and budget source link
  const budgetsel = document.querySelector(`#budgets-${farmcrop_pk}`)
  const info = document.querySelector(`#budget-info-${farmcrop_pk}`)
  const link = document.querySelector(`#budgetsource-${farmcrop_pk}`)
  let budget_id = budgetsel.value;
  let hasbudget = budget_id != ""
  let selopt = budgetsel.selectedOptions[0]
  let budgetsource = selopt.dataset[`budget-${farmcrop_pk}`]
  if (hasbudget) {
    info.innerHTML = "Budget set; any custom budget item values<br>" +
                     "will be lost if this selection is later changed."
    link.href = `/budgetsources/${farmyear_pk}/#${budgetsource}`
    link.classList.remove("invisible")
  } else {
    info.innerHTML = "Before adding a budget, please ensure that the<br>" +
                     "irrigation status is set correctly."
    link.href = '#'
    link.classList.add("invisible")
  }
}

function submitFormData(farmcrop_pk, farmyear_pk) {
  let xhr = new XMLHttpRequest();
  const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
  const budgetid = document.querySelector(`#budgets-${farmcrop_pk}`).value;
  const url = budgetid ==="" ? "deletebudget/" : "addbudget/";
  const data = JSON.stringify({budget: budgetid, farmcrop: farmcrop_pk});
  xhr.open("POST", url, true);
  xhr.setRequestHeader('Content-Type', 'application/json'); 
  xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest'); 
  xhr.setRequestHeader('X-CSRFToken', csrftoken); 
  xhr.send(data);
  xhr.onload = function() {
    setinfo(farmcrop_pk, farmyear_pk);
  }
}
