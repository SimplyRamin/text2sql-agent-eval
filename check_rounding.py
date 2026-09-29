from evals.scorer import run_query

gt = "SELECT o.order_status, ROUND(AVG(r.review_score), 2) AS avg_score FROM orders o JOIN order_reviews r ON o.order_id = r.order_id GROUP BY o.order_status;"
generated = "SELECT o.order_status, AVG(r.review_score) AS average_review_score FROM orders o JOIN order_reviews r ON o.order_id = r.order_id GROUP BY o.order_status;"

print("ground truth:", run_query(gt))
print("generated:", run_query(generated))
