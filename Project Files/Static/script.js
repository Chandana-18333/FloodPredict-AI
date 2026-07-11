// Fetch and display prediction log history from database
async function loadHistory() {
    const historyTableBody = document.getElementById('historyTableBody');
    if (!historyTableBody) return;
    
    try {
        const response = await fetch('/history');
        if (!response.ok) throw new Error('Failed to load history');
        
        const data = await response.json();
        
        if (data.history.length === 0) {
            historyTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">No prediction records found under your profile.</td></tr>`;
            return;
        }
        
        historyTableBody.innerHTML = data.history.map(row => {
            // Parse SQLite UTC timestamp and convert to local timezone
            const dateStr = new Date(row.date.replace(' ', 'T') + 'Z').toLocaleString();
            const badgeClass = row.flood ? 'badge-danger' : 'badge-safe';
            const badgeText = row.flood ? 'HIGH RISK' : 'LOW RISK';
            return `
                <tr>
                    <td style="color: var(--text-muted); font-size: 0.8rem;">${dateStr}</td>
                    <td>${row.temp.toFixed(1)}</td>
                    <td>${row.humidity.toFixed(0)}%</td>
                    <td>${row.cloud_cover.toFixed(0)}%</td>
                    <td>${row.annual_rainfall.toFixed(1)}</td>
                    <td>${row.jun_sep.toFixed(1)}</td>
                    <td class="${row.flood ? 'risk-color' : 'safe-color'}" style="font-weight: 700;">${row.flood_probability.toFixed(1)}%</td>
                    <td><span class="badge ${badgeClass}">${badgeText}</span></td>
                </tr>
            `;
        }).join('');
        
    } catch (err) {
        console.error(err);
        historyTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--danger); padding: 20px;">Failed to fetch prediction history log from backend.</td></tr>`;
    }
}

// Form submission handler
document.getElementById('predictionForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const defaultState = document.getElementById('defaultState');
    const resultCard = document.getElementById('resultCard');
    const riskBadge = document.getElementById('riskBadge');
    const riskTitle = document.getElementById('riskTitle');
    const probabilityFill = document.getElementById('probabilityFill');
    const probabilityText = document.getElementById('probabilityText');
    const floodProbVal = document.getElementById('floodProbVal');
    const safeProbVal = document.getElementById('safeProbVal');
    const recList = document.getElementById('recommendationList');

    // Build the payload
    const payload = {
        temp: document.getElementById('temp').value,
        humidity: document.getElementById('humidity').value,
        cloud_cover: document.getElementById('cloud_cover').value,
        annual_rainfall: document.getElementById('annual_rainfall').value,
        jan_feb: document.getElementById('jan_feb').value,
        mar_may: document.getElementById('mar_may').value,
        jun_sep: document.getElementById('jun_sep').value,
        oct_dec: document.getElementById('oct_dec').value,
        avg_june: document.getElementById('avg_june').value,
        sub_index: document.getElementById('sub_index').value
    };

    // Transition state
    defaultState.style.display = 'none';
    resultCard.style.display = 'block';
    
    // Set pending class & titles
    resultCard.className = 'card result-card';
    riskBadge.innerText = 'CALCULATING';
    riskTitle.innerText = 'Running predictive algorithms...';
    probabilityFill.style.width = '0%';
    probabilityText.innerText = 'Processing...';

    try {
        const response = await fetch('/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error('API server returned an error state');
        }

        const result = await response.json();
        
        // Dynamic styling changes based on the prediction
        if (result.flood) {
            resultCard.className = 'card result-card danger-state';
            riskBadge.innerText = 'HIGH RISK';
            riskTitle.innerText = 'WARNING: CRITICAL FLOOD RISK DETECTED';
            
            recList.innerHTML = `
                <li><strong>Evacuation readiness:</strong> Put your emergency evacuation plan into action. Pack essentials and documents.</li>
                <li><strong>High ground:</strong> Avoid low-lying areas, underground spaces, and basement living units.</li>
                <li><strong>Local monitoring:</strong> Stay tuned to official weather channels and disaster response alerts.</li>
                <li><strong>Utilities check:</strong> Be prepared to turn off main electricity breakers and gas valves if water levels rise.</li>
            `;
        } else {
            resultCard.className = 'card result-card safe-state';
            riskBadge.innerText = 'LOW RISK';
            riskTitle.innerText = 'STATUS NOMINAL: LOW RISK LEVEL';
            
            recList.innerHTML = `
                <li><strong>Routine precautions:</strong> Standard weather safety practices are advised. Maintain clear storm drains.</li>
                <li><strong>Rain protection:</strong> Standard precipitation is expected; carry umbrellas/raincoats.</li>
                <li><strong>Information updates:</strong> Monitor seasonal forecasts for sudden change patterns.</li>
            `;
        }

        // Animate progress gauge and metrics text
        const floodProb = result.flood_probability;
        const safeProb = result.no_flood_probability;
        
        setTimeout(() => {
            probabilityFill.style.width = `${floodProb}%`;
            probabilityText.innerText = `${floodProb.toFixed(1)}% risk factor`;
            floodProbVal.innerText = `${floodProb.toFixed(1)}%`;
            safeProbVal.innerText = `${safeProb.toFixed(1)}%`;
            
            // Reload prediction history
            loadHistory();
        }, 50);

    } catch (err) {
        resultCard.className = 'card result-card danger-state';
        riskBadge.innerText = 'ERROR';
        riskTitle.innerText = 'Error running predictive analysis';
        probabilityText.innerText = 'Failed to fetch prediction';
        floodProbVal.innerText = '--';
        safeProbVal.innerText = '--';
        recList.innerHTML = `<li>Could not communicate with the local model API backend. Make sure app.py is running.</li>`;
        console.error(err);
    }
});

// Load history initially when page is loaded
document.addEventListener('DOMContentLoaded', loadHistory);
