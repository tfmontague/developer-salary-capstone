import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# Load the cleaned dataset
data = pd.read_csv("Transformed_Developer_Survey_Data.csv")

# Separate features and target variable
X = data.drop("TotalComp", axis=1)  # Replace 'TotalComp' with the name of your target column if different
y = data["TotalComp"]

# Convert categorical features to dummy variables
X = pd.get_dummies(X, drop_first=True)

# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Initialize the Random Forest Regressor
best_forest_model = RandomForestRegressor(random_state=42, n_estimators=100)

# Train the model
best_forest_model.fit(X_train, y_train)

# Evaluate the model (optional, for checking performance before saving)
y_pred = best_forest_model.predict(X_test)
print("Mean Absolute Error:", mean_absolute_error(y_test, y_pred))
print("Mean Squared Error:", mean_squared_error(y_test, y_pred))
print("R^2 Score:", r2_score(y_test, y_pred))

# Save the trained model
joblib.dump(best_forest_model, "best_forest_model_simplified.pkl")

# Save the columns used in the model
model_columns = X.columns.tolist()
joblib.dump(model_columns, "model_columns_simplified.pkl")

# Also save model columns as CSV for easy reference
pd.DataFrame(model_columns, columns=["Feature"]).to_csv("model_columns_simplified.csv", index=False)

print("Model and columns saved successfully.")

