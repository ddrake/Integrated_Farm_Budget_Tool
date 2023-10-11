function setinfo(hasbudget, farmcrop_pk) {
  let info = document.querySelector(`#budget-info-${farmcrop_pk}`)
  info.innerHTML = hasbudget ? ("Budget set; any custom budget item values<br>" +
    "will be lost if this selection is later changed.")
    : ("Before adding a budget, please ensure that the<br>" +
       "irrigation status is set correctly.");
}

function submitFormData(farmcrop_pk) {
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
    setinfo(budgetid !== "");
  }
}

function addBudgetLink(farmyear_pk, farmcrop_pk, budget_id) {
  const info = document.querySelector(`#budget-info-${farmcrop_pk}`)
  const budgetLink = document.createElement("a");
  const linkText = document.createTextNode('Budget Source')
  budgetLink.appendChild(linkText)
  budgetLink.setAttribute('href', `/budgetsources/${farmyear_pk}#${budget_id}`)
  budgetLink.setAttribute('class', 'block mt-2 text-sm text-indigo-800 hover:text-indigo-600')
  info.after(budgetLink);
}
