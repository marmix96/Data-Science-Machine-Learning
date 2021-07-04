# ex4 a
set.seed(8)
n = 50
p = 15
X = data.frame(matrix(NA, n, p))
X[, 1:10] = rnorm(n*10)
X[, 11:15] = apply(X, 1, function(x) rnorm(5, mean = 0.2 * x[1] + 0.4 * x[2] + 0.6 * x[3] + 0.8 * x[4] + 1.1 * x[5], sd = 1))
X$Y = apply(X, 1, function (x) rnorm(1, mean = 4 + 2 * x[1] - x[5] + 2.5 * x[7] + 1.5 * x[11] + 0.5 * x[13], sd = 1.5))

best_score = Inf
best_model = NA
for (enumeration in 1: (2^p-1)) {
  model = lm(X$Y ~ ., data = as.data.frame(X[, c(which(as.integer(intToBits(enumeration)) == 1))]))
  if (BIC(model) < best_score) {
    best_model = model
    best_score = BIC(model)
  }
}
print(best_model)

# 4b
library(glmnet)
lasso = glmnet(as.matrix(X[,1:15]), as.matrix(X$Y))
plot(lasso, xvar = "lambda", label = T)
plot(lasso, label = T)

cv_lasso = cv.glmnet(as.matrix(X[,1:15]), as.matrix(X$Y))
plot(cv_lasso)

cv_lasso$lambda.min
log(cv_lasso$lambda.min)
cv_lasso$lambda.1se
log(cv_lasso$lambda.1se)

model_coef = coef(cv_lasso, s = 'lambda.min')
print(model_coef)

# Το shrinkage factor δείχνει πόσο μειώνεται η διασπορά του μοντέλου, και όχι πόσο συμπιέστηκαν καθαρά τα coefficients
zblasso = model_coef[-1] * apply(X[, 1:15], 2, sd)
zbols = coef(lm(X$Y ~ ., data = X[, 1:15]))[-1] * apply(X[, 1:15], 2, sd)
s = sum(abs(zblasso)) / sum(abs(zbols))
print(paste("s = ", signif(s, 4)))
