// API базовый URL
const API_BASE = 'http://localhost:8000/api/v1';

// Состояние приложения
let currentRoute = null;
let currentStop = null;
let forecastChart = null;
let analyticsChart = null;

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    loadRoutes();
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
                loadRoutesForAnalytics();
            }
        });
    });
}

// Настройка обработчиков событий
function setupEventListeners() {
    document.getElementById('route-select').addEventListener('change', async (e) => {
        const routeId = e.target.value;
        if (routeId) {
            await loadStops(routeId);
            currentRoute = routeId;
        }
    });
    
    document.getElementById('stop-select').addEventListener('change', async (e) => {
        const stopId = e.target.value;
        if (stopId && currentRoute) {
            currentStop = stopId;
            await loadCurrentLoad(currentRoute, stopId);
            await loadForecast(currentRoute, stopId);
        }
    });
    
    document.getElementById('load-analytics').addEventListener('click', () => {
        loadAnalytics();
    });
}

// Загрузка списка маршрутов
async function loadRoutes() {
    try {
        const response = await fetch(`${API_BASE}/routes`);
        const routes = await response.json();
        
        const select = document.getElementById('route-select');
        select.innerHTML = '<option value="">Выберите маршрут</option>';
        
        routes.forEach(route => {
            const option = document.createElement('option');
            option.value = route.id;
            option.textContent = `Маршрут ${route.number} - ${route.name || ''}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Ошибка загрузки маршрутов:', error);
        alert('Не удалось загрузить маршруты');
    }
}

// Загрузка остановок маршрута
async function loadStops(routeId) {
    try {
        const response = await fetch(`${API_BASE}/passengers/routes/${routeId}/stops`);
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
    }
}

// Загрузка текущей загруженности
async function loadCurrentLoad(routeId, stopId) {
    try {
        const response = await fetch(`${API_BASE}/passengers/current-load/${routeId}?stop_id=${stopId}`);
        const data = await response.json();
        
        document.getElementById('route-number').textContent = data.route_number;
        document.getElementById('stop-name').textContent = data.stop_name;
        document.getElementById('people-count').textContent = data.current_load;
        document.getElementById('load-percentage').textContent = data.load_percentage.toFixed(1);
        document.getElementById('updated-at').textContent = new Date(data.updated_at).toLocaleString('ru-RU');
        
        // Обновление индикатора статуса
        const indicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        indicator.className = 'status-indicator ' + data.load_status;
        
        const statusMap = {
            'free': 'Свободно',
            'medium': 'Средняя загрузка',
            'full': 'Заполнено'
        };
        statusText.textContent = statusMap[data.load_status] || data.load_status;
        
        // Отображение ближайших автобусов
        displayBuses(data.next_buses);
        
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
            <div class="bus-number">Автобус ${bus.vehicle_number}</div>
            <div class="bus-load">
                <span class="status-indicator ${bus.load_status}"></span>
                Загруженность: ${bus.load_percentage.toFixed(1)}%
            </div>
            <div>Пассажиров: ${bus.current_load}/${bus.max_capacity || '?'}</div>
        </div>
    `).join('');
}

// Загрузка прогноза
async function loadForecast(routeId, stopId) {
    try {
        const response = await fetch(`${API_BASE}/passengers/forecast/${routeId}?stop_id=${stopId}&hours=24`);
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
                    label: 'Прогноз загруженности (%)',
                    data: forecasts.map(f => f.predicted_load),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    } catch (error) {
        console.error('Ошибка загрузки прогноза:', error);
    }
}

// Загрузка маршрутов для аналитики
async function loadRoutesForAnalytics() {
    try {
        const response = await fetch(`${API_BASE}/routes`);
        const routes = await response.json();
        
        const select = document.getElementById('analytics-route');
        select.innerHTML = '<option value="">Выберите маршрут</option>';
        
        routes.forEach(route => {
            const option = document.createElement('option');
            option.value = route.id;
            option.textContent = `Маршрут ${route.number}`;
            select.appendChild(option);
        });
        
        select.addEventListener('change', async (e) => {
            const routeId = e.target.value;
            if (routeId) {
                await loadStopsForAnalytics(routeId);
            }
        });
    } catch (error) {
        console.error('Ошибка загрузки маршрутов:', error);
    }
}

// Загрузка остановок для аналитики
async function loadStopsForAnalytics(routeId) {
    try {
        const response = await fetch(`${API_BASE}/passengers/routes/${routeId}/stops`);
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
    const routeId = document.getElementById('analytics-route').value;
    const stopId = document.getElementById('analytics-stop').value;
    const period = document.getElementById('period').value;
    
    if (!routeId) {
        alert('Выберите маршрут');
        return;
    }
    
    try {
        // Загрузка статистики
        const statsResponse = await fetch(
            `${API_BASE}/analytics/load-statistics/${routeId}?stop_id=${stopId || ''}&days=${period}`
        );
        const stats = await statsResponse.json();
        
        // Отображение графика
        displayAnalyticsChart(stats.statistics);
        
        // Загрузка часов пик
        const peakResponse = await fetch(
            `${API_BASE}/analytics/peak-hours/${routeId}?stop_id=${stopId || ''}&days=${period}`
        );
        const peakData = await peakResponse.json();
        
        displayPeakHours(peakData.peak_hours);
        
        document.getElementById('analytics-results').classList.remove('hidden');
    } catch (error) {
        console.error('Ошибка загрузки аналитики:', error);
        alert('Не удалось загрузить аналитику');
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
                    label: 'Средняя загруженность (%)',
                    data: statistics.map(s => s.avg_load),
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    yAxisID: 'y'
                },
                {
                    label: 'Среднее количество людей',
                    data: statistics.map(s => s.total_people / (s.count || 1)),
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
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
                Загруженность: ${hour.average_load_percentage.toFixed(1)}% | 
                Людей: ${hour.average_people_count.toFixed(1)}
            </div>
        </div>
    `).join('');
}



