document.addEventListener('DOMContentLoaded', function() {
    const targetList = document.getElementById('targetList');
    const userId = targetList.dataset.userId;

    targetList.addEventListener('click', function(event) {
        if (event.target.classList.contains('select-target')) {
            const targetId = event.target.getAttribute('data-target-id');
            redirectToAttackPage(userId, targetId);
        }
    });

    function redirectToAttackPage(userId, targetId) {
        window.location.href = `/user/${userId}/attack/${targetId}`;
    }
}); 