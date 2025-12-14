// API базовый URL
const API_BASE = 'http://localhost:8000/api/v1';

// Состояние приложения
let currentStop = null;
let forecastChart = null;
let analyticsChart = null;

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    loadStops();
    loadStopsForAnalytics();
    setupEventListeners();
});

// Настройка навигации
function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tab = e.target.dataset.tab;
            
            // Обновление активных кнопок
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            // Переключение панелей
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.getElementById(`${tab}-panel`).classList.add('active');
            
            if (tab === 'analytics') {
                loadStopsForAnalytics();
            }
        });
    });
}

// Настройка обработчиков событий
function setupEventListeners() {
    document.getElementById('stop-select').addEventListener('change', async (e) => {
        const stopId = e.target.value;
        if (stopId) {
            currentStop = stopId;
            await loadCurrentLoad(stopId);
            await loadForecast(stopId);
        }
    });
    
    document.getElementById('load-analytics').addEventListener('click', () => {
        loadAnalytics();
    });
}

// Загрузка списка остановок
async function loadStops() {
    try {
        const response = await fetch(`${API_BASE}/passengers/stops`);
        const stops = await response.json();
        
        const select = document.getElementById('stop-select');
        select.innerHTML = '<option value="">Выберите остановку</option>';
        
        stops.forEach(stop => {
            const option = document.createElement('option');
            option.value = stop.id;
            option.textContent = stop.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Ошибка загрузки остановок:', error);
        alert('Не удалось загрузить остановки');
    }
}

// Загрузка текущей загруженности
async function loadCurrentLoad(stopId) {
    try {
        const response = await fetch(`${API_BASE}/passengers/current-load/${stopId}`);
        const data = await response.json();
        
        document.getElementById('stop-name').textContent = data.stop_name;
        document.getElementById('people-count').textContent = data.people_count;
        
        // Вычисляем процент загруженности (предполагаем максимум 50 человек)
        const maxCapacity = 50;
        const loadPercentage = (data.people_count / maxCapacity) * 100;
        document.getElementById('load-percentage').textContent = loadPercentage.toFixed(1);
        document.getElementById('updated-at').textContent = new Date(data.updated_at).toLocaleString('ru-RU');
        
        // Обновление индикатора статуса
        const indicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        indicator.className = 'status-indicator ' + data.load_status;
        
        const statusMap = {
            'free': 'Свободно',
            'medium': 'Средняя загрузка',
            'crowded': 'Заполнено'
        };
        statusText.textContent = statusMap[data.load_status] || data.load_status;
        
        // Отображение ближайших автобусов
        displayBuses(data.recent_buses || []);
        
        // Показать панель
        document.getElementById('current-load-info').classList.remove('hidden');
    } catch (error) {
        console.error('Ошибка загрузки загруженности:', error);
        alert('Не удалось загрузить данные о загруженности');
    }
}

// Отображение списка автобусов
function displayBuses(buses) {
    const container = document.getElementById('buses-list');
    
    if (buses.length === 0) {
        container.innerHTML = '<p>Нет данных об автобусах</p>';
        return;
    }
    
    container.innerHTML = buses.map(bus => `
        <div class="bus-card">
            <div class="bus-number">Автобус ${bus.bus_number || 'Неизвестно'}</div>
            <div>Обнаружен: ${new Date(bus.detected_at).toLocaleString('ru-RU')}</div>
            <div>Уверенность: ${(bus.confidence * 100).toFixed(1)}%</div>
        </div>
    `).join('');
}

// Загрузка прогноза
async function loadForecast(stopId) {
    try {
        const response = await fetch(`${API_BASE}/passengers/forecast/${stopId}?hours=24`);
        const forecasts = await response.json();
        
        if (forecasts.length === 0) {
            return;
        }
        
        const ctx = document.getElementById('forecast-chart');
        
        if (forecastChart) {
            forecastChart.destroy();
        }
        
        forecastChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: forecasts.map(f => new Date(f.forecast_time).toLocaleString('ru-RU')),
                datasets: [{
                    label: 'Прогноз количества людей',
                    data: forecasts.map(f => f.predicted_people_count),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error('Ошибка загрузки прогноза:', error);
    }
}

// Загрузка остановок для аналитики
async function loadStopsForAnalytics() {
    try {
        const response = await fetch(`${API_BASE}/passengers/stops`);
        const stops = await response.json();
        
        const select = document.getElementById('analytics-stop');
        select.innerHTML = '<option value="">Все остановки</option>';
        
        stops.forEach(stop => {
            const option = document.createElement('option');
            option.value = stop.id;
            option.textContent = stop.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Ошибка загрузки остановок:', error);
    }
}

// Загрузка аналитики
async function loadAnalytics() {
    const stopId = document.getElementById('analytics-stop').value;
    const period = document.getElementById('period').value;
    
    if (!stopId) {
        alert('Выберите остановку');
        return;
    }
    
    try {
        // Загрузка статистики
        const statsResponse = await fetch(
            `${API_BASE}/analytics/load-statistics/${stopId}?days=${period}`
        );
        if (!statsResponse.ok) {
            throw new Error(`HTTP error! status: ${statsResponse.status}`);
        }
        const stats = await statsResponse.json();
        
        // Проверяем, есть ли данные
        if (!stats.statistics || stats.statistics.length === 0) {
            alert(stats.message || 'Нет данных за указанный период. Убедитесь, что задачи мониторинга запущены и собирают данные.');
            return;
        }
        
        // Отображение графика
        displayAnalyticsChart(stats.statistics);
        
        // Загрузка часов пик
        const peakResponse = await fetch(
            `${API_BASE}/analytics/peak-hours/${stopId}?days=${period}`
        );
        if (!peakResponse.ok) {
            throw new Error(`HTTP error! status: ${peakResponse.status}`);
        }
        const peakData = await peakResponse.json();
        
        displayPeakHours(peakData.peak_hours || []);
        
        document.getElementById('analytics-results').classList.remove('hidden');
    } catch (error) {
        console.error('Ошибка загрузки аналитики:', error);
        alert('Не удалось загрузить аналитику: ' + error.message);
    }
}

// Отображение графика аналитики
function displayAnalyticsChart(statistics) {
    const ctx = document.getElementById('analytics-chart');
    
    if (analyticsChart) {
        analyticsChart.destroy();
    }
    
    analyticsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: statistics.map(s => new Date(s.timestamp).toLocaleString('ru-RU')),
            datasets: [
                {
                    label: 'Среднее количество людей',
                    data: statistics.map(s => s.avg_people || 0),
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    yAxisID: 'y'
                },
                {
                    label: 'Общее количество людей',
                    data: statistics.map(s => s.total_people || 0),
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    yAxisID: 'y1'
                },
                {
                    label: 'Автобусы',
                    data: statistics.map(s => s.total_buses || 0),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    max: 100
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true
                }
            }
        }
    });
}

// Отображение часов пик
function displayPeakHours(peakHours) {
    const container = document.getElementById('peak-hours-list');
    
    if (peakHours.length === 0) {
        container.innerHTML = '<p>Нет данных о часах пик</p>';
        return;
    }
    
    container.innerHTML = peakHours.slice(0, 10).map(hour => `
        <div class="peak-hour-item">
            <div>
                <strong>${hour.hour}:00</strong>
            </div>
            <div>
                Людей: ${hour.average_people_count.toFixed(1)} | 
                Автобусов: ${hour.average_buses_count.toFixed(1)}
            </div>
        </div>
    `).join('');
}




