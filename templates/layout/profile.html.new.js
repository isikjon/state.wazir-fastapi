        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script>
            // Функция для копирования ID пользователя в буфер обмена
            function copyUserId() {
                const userId = document.getElementById('user-id').innerText;
                
                // Создаем временный элемент для копирования
                const el = document.createElement('textarea');
                el.value = userId;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                
                // Показываем уведомление об успешном копировании
                alert('ID пользователя скопирован');
            }
            
            // Функции для работы с кэшем данных о погоде
            function saveWeatherToCache(data) {
                const now = new Date().getTime();
                const weatherData = {
                    data: data,
                    timestamp: now
                };
                localStorage.setItem('weatherData', JSON.stringify(weatherData));
            }
            
            function getWeatherFromCache() {
                const weatherDataStr = localStorage.getItem('weatherData');
                if (!weatherDataStr) return null;
                
                const weatherData = JSON.parse(weatherDataStr);
                const now = new Date().getTime();
                
                // Считаем кэш устаревшим, если прошло больше часа
                if (now - weatherData.timestamp > 3600000) {
                    localStorage.removeItem('weatherData');
                    return null;
                }
                
                return weatherData.data;
            }
            
            // Функции для работы с кэшем данных о курсе валют
            function saveCurrencyToCache(data) {
                const now = new Date().getTime();
                const currencyData = {
                    data: data,
                    timestamp: now
                };
                localStorage.setItem('currencyData', JSON.stringify(currencyData));
            }
            
            function getCurrencyFromCache() {
                const currencyDataStr = localStorage.getItem('currencyData');
                if (!currencyDataStr) return null;
                
                const currencyData = JSON.parse(currencyDataStr);
                const now = new Date().getTime();
                
                // Считаем кэш устаревшим, если прошло больше 3 часов
                if (now - currencyData.timestamp > 10800000) {
                    localStorage.removeItem('currencyData');
                    return null;
                }
                
                return currencyData.data;
            }
            
            // Функция для отображения данных о погоде
            function displayWeatherData(weatherData) {
                if (weatherData.temp) {
                    $('#weather-temp').text(weatherData.temp + '°C');
                }
                if (weatherData.iconHtml) {
                    $('#weather-icon-container').html(weatherData.iconHtml);
                }
            }
            
            // Функция для отображения данных о курсе валют
            function displayCurrencyData(currencyData) {
                if (currencyData.rate) {
                    $('#currency-rate').text(currencyData.rate);
                }
            }
            
            $(document).ready(function() {
                // Обработка переключения табов
                $('.tab').on('click', function() {
                    const target = $(this).data('target');
                    
                    // Убираем активный класс со всех табов
                    $('.tab').removeClass('active');
                    $(this).addClass('active');
                    
                    // Показываем нужный контент
                    $('.tab-content').removeClass('active');
                    $('#' + target).addClass('active');
                });
                
                // Обработка клика по навигационным элементам
                $('.nav-item').on('click', function() {
                    $('.nav-item').removeClass('active').addClass('text-gray-500');
                    $(this).addClass('active').removeClass('text-gray-500');
                });
                
                // Функция для получения данных о погоде через API
                function getWeather() {
                    // Сначала проверяем, есть ли кэшированные данные
                    const cachedWeather = getWeatherFromCache();
                    if (cachedWeather) {
                        // Если есть кэшированные данные, сразу их отображаем
                        displayWeatherData(cachedWeather);
                        return;
                    }
                    
                    // Если кэша нет или он устарел, запрашиваем данные с нашего API
                    $.ajax({
                        url: '/api/v1/weather/current',
                        method: 'GET',
                        success: function(data) {
                            if (data && data.temperature) {
                                // Определяем иконку на основе температуры
                                var iconHtml;
                                if (data.temperature > 15) {
                                    // Теплая погода - солнце
                                    iconHtml = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>';
                                } else {
                                    // Прохладная погода - облачно
                                    iconHtml = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c8aa0" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>';
                                }
                                
                                // Сохраняем данные в кэш
                                const weatherData = {
                                    temp: data.temperature,
                                    iconHtml: iconHtml
                                };
                                saveWeatherToCache(weatherData);
                                
                                // Отображаем данные
                                displayWeatherData(weatherData);
                            } else {
                                showFallbackWeather();
                            }
                        },
                        error: function() {
                            showFallbackWeather();
                        }
                    });
                }
                
                // Функция для отображения резервных данных о погоде
                function showFallbackWeather() {
                    var iconHtml = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="weather-icon"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>';
                    displayWeatherData({
                        temp: '20',
                        iconHtml: iconHtml
                    });
                }
                
                // Функция для получения курса валют через API
                function getCurrencyRate() {
                    // Сначала проверяем, есть ли кэшированные данные
                    const cachedCurrency = getCurrencyFromCache();
                    if (cachedCurrency) {
                        // Если есть кэшированные данные, сразу их отображаем
                        displayCurrencyData(cachedCurrency);
                        return;
                    }
                    
                    // Если кэша нет или он устарел, запрашиваем данные с нашего API
                    $.ajax({
                        url: '/api/v1/currency/usd',
                        method: 'GET',
                        success: function(data) {
                            if (data && data.rate) {
                                // Сохраняем данные в кэш
                                const currencyData = {
                                    rate: data.rate
                                };
                                saveCurrencyToCache(currencyData);
                                
                                // Отображаем данные
                                displayCurrencyData(currencyData);
                            } else {
                                showFallbackCurrency();
                            }
                        },
                        error: function() {
                            showFallbackCurrency();
                        }
                    });
                }
                
                // Функция для отображения резервных данных о курсе валют
                function showFallbackCurrency() {
                    displayCurrencyData({
                        rate: '69.8'
                    });
                }
                
                // Получаем данные о погоде и курсе валют
                getWeather();
                getCurrencyRate();
            });
        </script>
    </body>
</html>
