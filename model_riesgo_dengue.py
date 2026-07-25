import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parent


def load_dimensions(root: Path):
    tiempo = pd.read_csv(root / 'DIMENSIONES' / 'DIM_TIEMPO.csv', parse_dates=['fecha'], dayfirst=True, low_memory=False)
    geografia = pd.read_csv(root / 'DIMENSIONES' / 'DIM_GEOGRAFIA.csv', low_memory=False)
    return tiempo, geografia


def aggregate_cases_by_state_quarter(root: Path, tiempo: pd.DataFrame, geografia: pd.DataFrame) -> pd.DataFrame:
    usecols = ['id_tiempo', 'id_geografia']
    casos = pd.read_csv(root / 'HECHOS' / 'FACT_CASOS_DENGUE.csv', usecols=usecols, low_memory=False)
    casos = casos.merge(tiempo[['id_tiempo', 'fecha']], on='id_tiempo', how='left')
    casos = casos.merge(geografia[['id_geografia', 'entidad']], on='id_geografia', how='left')
    casos = casos.dropna(subset=['fecha', 'entidad'])
    casos['year'] = casos['fecha'].dt.year
    casos['quarter'] = casos['fecha'].dt.quarter
    casos_q = casos.groupby(['entidad', 'year', 'quarter'], as_index=False).size().rename(columns={'size': 'cases'})
    return casos_q


def aggregate_population_by_state_year(root: Path, tiempo: pd.DataFrame, geografia: pd.DataFrame) -> pd.DataFrame:
    usecols = ['id_tiempo', 'id_geografia', 'poblacion']
    poblacion = pd.read_csv(root / 'HECHOS' / 'FACT_POBLACION.csv', usecols=usecols, low_memory=False)
    poblacion = poblacion.merge(tiempo[['id_tiempo', 'anio']], on='id_tiempo', how='left')
    poblacion = poblacion.merge(geografia[['id_geografia', 'entidad']], on='id_geografia', how='left')
    poblacion = poblacion.dropna(subset=['anio', 'entidad']).copy()
    poblacion['poblacion'] = pd.to_numeric(poblacion['poblacion'], errors='coerce')
    poblacion = poblacion.dropna(subset=['poblacion'])
    poblacion_agg = (
        poblacion.groupby(['entidad', 'anio'], as_index=False)['poblacion'].sum()
        .rename(columns={'anio': 'year'})
    )
    return poblacion_agg


def aggregate_climate_by_state_quarter(root: Path, tiempo: pd.DataFrame, geografia: pd.DataFrame) -> pd.DataFrame:
    usecols = ['id_tiempo', 'id_geografia', 'temp_max', 'temp_min', 'lluvia_acumulada', 'evapotranspiracion']
    clima = pd.read_csv(root / 'HECHOS' / 'FACT_CLIMA.csv', usecols=usecols, low_memory=False)
    clima = clima.merge(tiempo[['id_tiempo', 'fecha']], on='id_tiempo', how='left')
    clima = clima.merge(geografia[['id_geografia', 'entidad']], on='id_geografia', how='left')
    clima = clima.dropna(subset=['fecha', 'entidad']).copy()
    clima[['temp_max', 'temp_min', 'lluvia_acumulada', 'evapotranspiracion']] = clima[
        ['temp_max', 'temp_min', 'lluvia_acumulada', 'evapotranspiracion']
    ].apply(pd.to_numeric, errors='coerce')
    clima = clima.dropna(subset=['temp_max', 'temp_min', 'lluvia_acumulada', 'evapotranspiracion'])
    clima['year'] = clima['fecha'].dt.year
    clima['quarter'] = clima['fecha'].dt.quarter
    clima_q = (
        clima.groupby(['entidad', 'year', 'quarter'], as_index=False)
        .agg(
            temp_max_q=('temp_max', 'mean'),
            temp_min_q=('temp_min', 'mean'),
            lluvia_q=('lluvia_acumulada', 'sum'),
            evapotransp_q=('evapotranspiracion', 'mean'),
            lluvia_dias_q=('lluvia_acumulada', lambda x: (x > 0).sum()),
        )
    )
    return clima_q


def build_state_quarter_dataset(root: Path) -> pd.DataFrame:
    tiempo, geografia = load_dimensions(root)
    casos_q = aggregate_cases_by_state_quarter(root, tiempo, geografia)
    poblacion_agg = aggregate_population_by_state_year(root, tiempo, geografia)
    clima_q = aggregate_climate_by_state_quarter(root, tiempo, geografia)

    base = clima_q[['entidad', 'year', 'quarter']].drop_duplicates()
    data = base.merge(poblacion_agg, on=['entidad', 'year'], how='left')
    data = data.merge(casos_q, on=['entidad', 'year', 'quarter'], how='left')
    data = data.merge(clima_q, on=['entidad', 'year', 'quarter'], how='left', suffixes=('', '_clima'))
    data['cases'] = data['cases'].fillna(0).astype(int)
    data = data.dropna(subset=['poblacion'])
    data['incidence_rate'] = (data['cases'] / data['poblacion']) * 100_000
    data['quarter_order'] = data['year'] * 4 + data['quarter']
    return data.sort_values(['entidad', 'year', 'quarter']).reset_index(drop=True)


def add_lag_features(data: pd.DataFrame) -> pd.DataFrame:
    data = data.sort_values(['entidad', 'year', 'quarter']).copy()
    cols_to_lag = [
        'incidence_rate',
        'temp_max_q',
        'temp_min_q',
        'lluvia_q',
        'evapotransp_q',
        'lluvia_dias_q',
    ]
    for lag in [1, 2]:
        data[[f'{col}_lag{lag}' for col in cols_to_lag]] = (
            data.groupby('entidad')[cols_to_lag].shift(lag)
        )
    data['incidence_diff_lag1'] = data['incidence_rate_lag1'] - data['incidence_rate_lag2']
    data['lluvia_diff_lag1'] = data['lluvia_q_lag1'] - data['lluvia_q_lag2']
    data['temp_max_diff_lag1'] = data['temp_max_q_lag1'] - data['temp_max_q_lag2']
    data['quarter_sin'] = np.sin(2 * np.pi * data['quarter'] / 4)
    data['quarter_cos'] = np.cos(2 * np.pi * data['quarter'] / 4)
    return data.dropna(subset=[f'incidence_rate_lag{lag}' for lag in [1, 2]]).reset_index(drop=True)


def label_risk_level(df: pd.DataFrame, low_pct=33.33, high_pct=66.67) -> tuple[pd.DataFrame, float, float]:
    cut_low = np.percentile(df['incidence_rate'], low_pct)
    cut_high = np.percentile(df['incidence_rate'], high_pct)

    def risk_label(rate: float) -> str:
        if rate <= cut_low:
            return 'BAJO'
        if rate <= cut_high:
            return 'MEDIO'
        return 'ALTO'

    df = df.copy()
    df['risk_level'] = df['incidence_rate'].apply(risk_label)
    return df, cut_low, cut_high


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    feature_cols = [
        'incidence_rate_lag1',
        'incidence_rate_lag2',
        'incidence_diff_lag1',
        'temp_max_q_lag1',
        'temp_min_q_lag1',
        'lluvia_q_lag1',
        'evapotransp_q_lag1',
        'lluvia_dias_q_lag1',
        'temp_max_q_lag2',
        'temp_min_q_lag2',
        'lluvia_q_lag2',
        'evapotransp_q_lag2',
        'lluvia_dias_q_lag2',
        'lluvia_diff_lag1',
        'temp_max_diff_lag1',
        'quarter',
        'quarter_sin',
        'quarter_cos',
    ]
    return df[feature_cols].copy(), feature_cols


def temporal_train_test_split(df: pd.DataFrame, test_fraction: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique_quarters = sorted(df['quarter_order'].unique())
    cutoff_index = int(len(unique_quarters) * (1 - test_fraction))
    cutoff_value = unique_quarters[cutoff_index]
    train = df[df['quarter_order'] <= cutoff_value].copy()
    test = df[df['quarter_order'] > cutoff_value].copy()
    return train, test


def train_decision_tree(X_train: pd.DataFrame, y_train: pd.Series) -> DecisionTreeClassifier:
    clf = DecisionTreeClassifier(max_depth=5, class_weight='balanced', random_state=42)
    clf.fit(X_train, y_train)
    return clf


def evaluate_model(model, X, y, dataset_name: str) -> None:
    y_pred = model.predict(X)
    print(f'=== Evaluación en {dataset_name} ===')
    print('Accuracy:', accuracy_score(y, y_pred))
    print('\nReporte de clasificación:')
    print(classification_report(y, y_pred, digits=3, zero_division=0))
    print('Matriz de confusión:')
    print(confusion_matrix(y, y_pred, labels=['BAJO', 'MEDIO', 'ALTO']))
    print()


def show_feature_importance(model, feature_names: list[str]) -> None:
    importances = model.feature_importances_
    importance_df = pd.DataFrame({'feature': feature_names, 'importance': importances})
    importance_df = importance_df.sort_values('importance', ascending=False)
    print('Importancia de variables:')
    print(importance_df.to_string(index=False, float_format='%.6f'))
    print()


def main() -> None:
    print('Cargando y agregando hechos a nivel estado-trimestre...')
    data = build_state_quarter_dataset(ROOT)
    data = add_lag_features(data)

    quarterly_order = data[['year', 'quarter', 'quarter_order']].drop_duplicates().sort_values(['quarter_order'])
    print('Trimestres disponibles:', quarterly_order.shape[0])
    print(quarterly_order.head())
    print(quarterly_order.tail())

    train_set, test_set = temporal_train_test_split(data, test_fraction=0.2)
    train_set, cut_low, cut_high = label_risk_level(train_set)
    test_set = test_set.copy()
    test_set['risk_level'] = test_set['incidence_rate'].apply(
        lambda rate: 'BAJO' if rate <= cut_low else 'MEDIO' if rate <= cut_high else 'ALTO'
    )

    print(f'Umbrales de incidencia (train): BAJO<= {cut_low:.3f}, MEDIO<= {cut_high:.3f}, ALTO> {cut_high:.3f}')
    print('Distribución de clases en train:')
    print(train_set['risk_level'].value_counts(normalize=False).to_string())
    print('Distribución de clases en test:')
    print(test_set['risk_level'].value_counts(normalize=False).to_string())
    print()

    X_train, feature_names = prepare_features(train_set)
    y_train = train_set['risk_level']
    X_test, _ = prepare_features(test_set)
    y_test = test_set['risk_level']

    print('Entrenando modelo interpretable...')
    model = train_decision_tree(X_train, y_train)
    evaluate_model(model, X_train, y_train, 'Entrenamiento')
    evaluate_model(model, X_test, y_test, 'Prueba')
    show_feature_importance(model, feature_names)

    output_path = ROOT / 'estado_trimestre_riesgo.csv'
    data[['entidad', 'year', 'quarter', 'cases', 'poblacion', 'incidence_rate']].to_csv(output_path, index=False)
    print(f'Dataset agregado exportado a: {output_path}')


if __name__ == '__main__':
    main()
