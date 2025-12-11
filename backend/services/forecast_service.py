"""
Сервис прогнозирования загруженности
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from prophet import Prophet
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from core.models import LoadData, Stop


class ForecastService:
    """Сервис для построения прогнозов загруженности"""
    
    def __init__(self):
        self.prophet_models = {}  # Кеш моделей для разных маршрутов
    
    def prepare_time_series_data(self, db: Session, 
                                 stop_id: int, 
                                 days: int = 30) -> pd.DataFrame:
        """
        Подготовка данных временного ряда для прогнозирования
        
        Args:
            db: сессия БД
            stop_id: ID остановки
            days: количество дней истории для анализа
            
        Returns:
            DataFrame с временным рядом
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = db.query(LoadData).filter(
            and_(
                LoadData.stop_id == stop_id,
                LoadData.timestamp >= start_date,
                LoadData.timestamp <= end_date
            )
        )
        
        # Агрегация по часам
        load_data = query.order_by(LoadData.timestamp).all()
        
        if not load_data:
            return pd.DataFrame()
        
        # Создание DataFrame
        data = []
        for record in load_data:
            data.append({
                'ds': record.timestamp,
                'y': record.people_count  # Используем количество людей вместо процента
            })
        
        df = pd.DataFrame(data)
        df = df.groupby(pd.Grouper(key='ds', freq='H')).agg({
            'y': 'mean'
        }).reset_index()
        
        return df
    
    def forecast_with_prophet(self, df: pd.DataFrame, periods: int = 24) -> Dict:
        """
        Прогнозирование с использованием Prophet
        
        Args:
            df: DataFrame с историческими данными
            periods: количество периодов для прогноза (часы)
            
        Returns:
            Словарь с прогнозами
        """
        if len(df) < 10:  # Недостаточно данных для прогноза
            return {
                'forecast': [],
                'error': 'Недостаточно исторических данных'
            }
        
        # Настройка модели Prophet
        model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=True,
            seasonality_mode='multiplicative'
        )
        
        model.fit(df)
        
        # Создание будущих дат
        future = model.make_future_dataframe(periods=periods, freq='H')
        forecast = model.predict(future)
        
        # Извлечение только прогнозных значений
        forecast_data = forecast.tail(periods)
        
        result = {
            'forecast': [],
            'error': None
        }
        
        for _, row in forecast_data.iterrows():
            result['forecast'].append({
                'timestamp': row['ds'],
                'predicted_load': max(0, row['yhat']),  # Количество людей (может быть больше 100)
                'lower_bound': max(0, row['yhat_lower']),
                'upper_bound': max(0, row['yhat_upper'])
            })
        
        return result
    
    def forecast_load(self, db: Session, 
                     route_id: Optional[int] = None,  # Оставлено для обратной совместимости
                     stop_id: Optional[int] = None,
                     hours: int = 24) -> Dict:
        """
        Построение прогноза загруженности
        
        Args:
            db: сессия БД
            route_id: ID маршрута (не используется, оставлено для обратной совместимости)
            stop_id: ID остановки
            hours: количество часов для прогноза
            
        Returns:
            Словарь с прогнозами
        """
        if not stop_id:
            return {
                'forecast': [],
                'error': 'Необходимо указать stop_id'
            }
        
        # Подготовка данных
        df = self.prepare_time_series_data(db, stop_id)
        
        if df.empty:
            return {
                'forecast': [],
                'error': 'Нет исторических данных'
            }
        
        # Прогнозирование
        return self.forecast_with_prophet(df, periods=hours)
    
    def get_current_load_status(self, load_percentage: float) -> str:
        """
        Определение статуса загруженности
        
        Args:
            load_percentage: процент загрузки (0-100)
            
        Returns:
            Статус: "free", "medium", "full"
        """
        if load_percentage < 40:
            return "free"
        elif load_percentage < 70:
            return "medium"
        else:
            return "full"


# Глобальный экземпляр сервиса
forecast_service = ForecastService()

