document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = document.querySelector(tab.dataset.tab);

            tabContents.forEach(tc => {
                tc.classList.remove('active');
            });
            target.classList.add('active');

            tabs.forEach(t => {
                t.classList.remove('active');
            });
            tab.classList.add('active');
        });
    });
});