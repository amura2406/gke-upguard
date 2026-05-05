
# Fix the routing by manually running the following:
# gcloud run services update gke-upgrade-risk-agent \
#  --vpc-egress=private-ranges-only \
#  --network=mock-upgrade-cluster-network \
#  --subnet=mock-upgrade-cluster-subnetwork \
#  --region=us-central1 \
#  --project=anggar-gke-upgrade-risk-agent

