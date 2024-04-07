import pandas as pd

data1 = {
  "age": [16, 14, 10],
  "qualified": [True, True, True]
}
df1 = pd.DataFrame(data1)

data2 = {
  "age": [55, 40],
  "qualified": [True, False]
}
df2 = pd.DataFrame(data2)

newdf = pd.concat([df1, df2], ignore_index=True)
print(newdf)