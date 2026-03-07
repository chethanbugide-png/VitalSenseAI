document.addEventListener('DOMContentLoaded', function() {
    
    // Assessment Form Submission
    const assessmentForm = document.getElementById('assessmentForm');
    if (assessmentForm) {
        assessmentForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Show loading overlay
            const overlay = document.getElementById('loadingOverlay');
            overlay.classList.remove('hidden');
            overlay.classList.add('flex');
            
            const formData = new FormData(assessmentForm);
            const data = {};
            
            // Gather multiple checkbox values into arrays
            const history = [];
            document.querySelectorAll('input[name="history"]:checked').forEach(cb => {
                history.push(cb.value);
            });
            data['history'] = history;
            
            const symptoms = [];
            document.querySelectorAll('input[name="symptoms"]:checked').forEach(cb => {
                symptoms.push(cb.value);
            });
            data['symptoms'] = symptoms;
            
            // Gather rest of data
            for (let [key, value] of formData.entries()) {
                if (key !== 'history' && key !== 'symptoms') {
                    data[key] = value;
                }
            }
            
            try {
                const response = await fetch('/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    // Hide loading overlay
                    overlay.classList.add('hidden');
                    overlay.classList.remove('flex');
                    
                    // Populate Modal Data
                    const modal = document.getElementById('resultsModal');
                    const modalContent = document.getElementById('resultsModalContent');
                    
                    const conditionBadge = document.getElementById('conditionBadge');
                    const conditionIcon = document.getElementById('conditionIcon');
                    const conditionText = document.getElementById('conditionText');
                    
                    // Reset classes
                    conditionBadge.className = 'inline-flex items-center justify-center gap-3 px-6 py-3 rounded-2xl border-2 font-black font-display text-3xl tracking-tight transition-colors';
                    
                    if (result.prediction === 0) {
                        conditionBadge.classList.add('bg-emerald-50', 'border-emerald-200', 'text-emerald-600');
                        conditionIcon.className = 'fa-solid fa-shield-check';
                        conditionText.innerText = 'Stable';
                    } else if (result.prediction === 1) {
                        conditionBadge.classList.add('bg-amber-50', 'border-amber-200', 'text-amber-600');
                        conditionIcon.className = 'fa-solid fa-eye';
                        conditionText.innerText = 'Attention Required';
                    } else {
                        conditionBadge.classList.add('bg-red-50', 'border-red-200', 'text-red-600');
                        conditionIcon.className = 'fa-solid fa-triangle-exclamation animate-pulse';
                        conditionText.innerText = 'Critical';
                    }
                    
                    document.getElementById('confidenceText').innerText = result.confidence_score + '%';
                    document.getElementById('doctorText').innerText = result.recommended_doctor;
                    
                    const actionsList = document.getElementById('actionsList');
                    actionsList.innerHTML = '';
                    const actions = result.recommended_actions.split(',');
                    actions.forEach(action => {
                        const li = document.createElement('li');
                        li.className = 'flex items-start gap-2';
                        li.innerHTML = `<i class="fa-solid fa-arrow-right text-medical-400 mt-1"></i> <span>${action.trim()}</span>`;
                        actionsList.appendChild(li);
                    });
                    
                    document.getElementById('viewDashboardBtn').href = `/dashboard?patient_id=${result.patient_id}`;
                    
                    // Show Modal with animation
                    modal.classList.remove('hidden');
                    modal.classList.add('flex');
                    // Small delay to allow display:flex to apply before animating opacity
                    setTimeout(() => {
                        modal.classList.remove('opacity-0');
                        modalContent.classList.remove('scale-95');
                        modalContent.classList.add('scale-100');
                    }, 50);
                    
                } else {
                    alert('Error: ' + result.error);
                    overlay.classList.add('hidden');
                    overlay.classList.remove('flex');
                }
            } catch (error) {
                console.error('Submission failed:', error);
                alert('An error occurred while connecting to the AI system.');
                overlay.classList.add('hidden');
                overlay.classList.remove('flex');
            }
        });
        
        // Modal Handlers
        const modal = document.getElementById('resultsModal');
        if (modal) {
            const closeModal = () => {
                modal.classList.add('opacity-0');
                const content = document.getElementById('resultsModalContent');
                content.classList.remove('scale-100');
                content.classList.add('scale-95');
                setTimeout(() => {
                    modal.classList.add('hidden');
                    modal.classList.remove('flex');
                }, 300);
            };
            
            document.getElementById('closeModalBtn').addEventListener('click', closeModal);
            document.getElementById('newAssessmentBtn').addEventListener('click', () => {
                closeModal();
                assessmentForm.reset();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        }
    }
});
