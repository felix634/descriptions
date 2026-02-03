"""Fix error messages in output Excel."""
import pandas as pd

df = pd.read_excel('zsalu_analysis.xlsx')

# Replace technical errors with user-friendly message
mask = df['AI_Description'].str.contains('Error', na=False)
df.loc[mask, 'AI_Description'] = "The Company's website does not work"

# Save back
df.to_excel('zsalu_analysis.xlsx', index=False)
print(f'Fixed {mask.sum()} errors')
print('File updated successfully!')
