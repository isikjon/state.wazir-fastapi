document.addEventListener('DOMContentLoaded', function () {
    // Проверяем, есть ли токен авторизации
    const token = localStorage.getItem('access_token');

    if (!token) {
        // Если нет токена, перенаправляем на страницу авторизации
        window.location.href = '/mobile/auth';
        return;
    }

    // Не добавляем панель пользователя на главной странице
    if (window.location.pathname === '/mobile' || window.location.pathname === '/mobile/') {
        return;
    }

    // Если пользователь авторизован, добавляем кнопку выхода
    const fullName = localStorage.getItem('full_name') || 'Пользователь';

    // Создаем элементы, если их еще нет
    if (!document.querySelector('.user-panel')) {
        const header = document.querySelector('header') || document.body;

        // Создаем элемент с данными пользователя и кнопкой выхода
        const userPanel = document.createElement('div');
        userPanel.className = 'user-panel fixed top-0 right-0 p-4 bg-white shadow-md rounded-bl-lg z-50 flex items-center';

        userPanel.innerHTML = `
            <div class="user-info mr-3">
                <div class="text-sm font-medium">${fullName}</div>
            </div>
            <a href="/mobile/logout" class="logout-btn bg-gray-200 hover:bg-gray-300 text-gray-700 px-3 py-1 rounded-md text-sm font-medium transition-colors">
                Выход
            </a>
        `;

        header.prepend(userPanel);
    }
}); 