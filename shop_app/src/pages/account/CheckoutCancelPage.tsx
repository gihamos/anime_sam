import { Link } from 'react-router-dom'
import { XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function CheckoutCancelPage() {
  return (
    <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <XCircle className="size-8 text-muted-foreground" />
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          <p className="text-sm text-muted-foreground">Souscription annulée — aucun paiement n'a été effectué.</p>
          <Button className="w-full" render={<Link to="/tarifs" />} nativeButton={false}>
            Retour aux tarifs
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
