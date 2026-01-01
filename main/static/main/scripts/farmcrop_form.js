    function scaleUpPercents() {
        document.querySelector("#id-farmcropform").reset();
        const matches = document.querySelectorAll(".percent");
        matches.forEach((fld) => {
            fld.value = +(parseFloat(fld.value)*100).toFixed(2);
        })
    }

    function updateBaseCoverageLevels(value) {
        let options = '<option value="">--------</option>\n';
        if (value !== '') {
            let farmlevels = [['0.5','50%'],['0.55','55%'],['0.6','60%'],['0.65','65%'],
                              ['0.7','70%'],['0.75','75%'],['0.8','80%'],['0.85','85%']];
            let ctylevels = [['0.7','70%'],['0.75','75%'],['0.8','80%'],['0.85','85%'],
                             ['0.9','90%']];
            let levels = value === '0' ? ctylevels : farmlevels;
            levels.forEach(opt => {
                options += `<option value=${opt[0]}>${opt[1]}</option>\n` 
            });
        }
        document.getElementById("base_coverage_level").innerHTML = options;
    }

    function manageScoAndProtFactor(value, crop_year) {
        let icropyear = parseInt(crop_year, 10)
        if (value !== '') {
            let scouse = document.getElementById("id_sco_use")
            let ecolevel = document.getElementById("eco_level")
            let prot = document.getElementById("id_prot_factor")
            if (value === '0') {
                ecolevel.value = '';
                if (icropyear < 2026) {
                  scouse.checked = false;
                  scouse.setAttribute('disabled', '')
                }
                ecolevel.setAttribute('disabled', '')
                prot.removeAttribute('disabled', '')
            } else {
                scouse.removeAttribute('disabled', '')
                ecolevel.removeAttribute('disabled', '')
                prot.value = '100';
                prot.setAttribute('disabled', '')
            }
        }
    }

    function lockAllInputs(lock) {
        if (lock) {
            document.getElementById("id_planted_acres").setAttribute('disabled', '')
            document.getElementById("ins_practice").setAttribute('disabled', '')
            document.getElementById("id_rate_yield").setAttribute('disabled', '')
            document.getElementById("id_adj_yield").setAttribute('disabled', '')
            document.getElementById("subcounty").setAttribute('disabled', '')
            document.getElementById("id_ta_use").setAttribute('disabled', '')
            document.getElementById("id_ye_use").setAttribute('disabled', '')
            document.getElementById("id_appr_yield").setAttribute('disabled', '')
        } else {
            document.getElementById("id_planted_acres").removeAttribute('disabled')
            document.getElementById("ins_practice").removeAttribute('disabled')
            document.getElementById("id_rate_yield").removeAttribute('disabled')
            document.getElementById("id_adj_yield").removeAttribute('disabled')
            document.getElementById("subcounty").removeAttribute('disabled')
            document.getElementById("id_ta_use").removeAttribute('disabled')
            document.getElementById("id_ye_use").removeAttribute('disabled')
            document.getElementById("id_appr_yield").removeAttribute('disabled')
        }
    }
